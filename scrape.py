import requests
import json
import sqlite3
import os
import time
from urllib.parse import urlparse
import concurrent.futures
import threading

# Headers from test123.txt
HEADERS = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'lang': 'en-us',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://www.pacdora.com/mockups/sachet-mockups?sort=popular',
    'sec-ch-ua': '"Not;A=Brand";v="8", "Chromium";v="150", "Brave";v="150"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sec-gpc': '1',
    'target_env': '',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
    'x-workspace-code': 'wsNlGsyWjIRc',
}

DB_NAME = 'extracted_data.db'
IMAGES_DIR = 'static/images'
JSON_DIR = 'data_dumps'

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)

db_lock = threading.Lock()

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    # The table already exists from the previous setup
    return conn

def download_image(url, item_num):
    if not url:
        return item_num, ""
    if url.startswith("//"):
        url = "https:" + url
        
    ext = os.path.splitext(urlparse(url).path)[1]
    if not ext:
        ext = '.png' # default
        
    filename = f"{item_num}{ext}"
    filepath = os.path.join(IMAGES_DIR, filename)
    
    if os.path.exists(filepath):
        return item_num, filename
        
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(r.content)
            return item_num, filename
    except Exception:
        pass
        
    return item_num, ""

def get_categories():
    with open('ctree.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    categories = []
    
    for top_level in data.get('data', []):
        class1 = top_level.get('name')
        
        for child in top_level.get('children', []):
            mockupNameKey = child.get('mockupNameKey')
            name = child.get('name')
            if mockupNameKey:
                categories.append({
                    'class1': class1,
                    'class2Bymodel': name,
                    'mockupNameKey': mockupNameKey
                })
                
    return categories

def scrape_category(cat_info, conn, existing_nums):
    mockupNameKey = cat_info['mockupNameKey']
    print(f"Scraping category: {mockupNameKey}")
    
    page = 1
    all_items = []
    
    while True:
        params = {
            'pageSize': '60',
            'current': str(page),
            'mockupNameKey': mockupNameKey,
            'type': 'blank',
            'sort': 'new',  # Changed to 'new' so newest items are first
            'offset': str((page - 1) * 60),
        }
        
        try:
            r = requests.get('https://www.pacdora.com/api/v2/models', params=params, headers=HEADERS, timeout=15)
            data = r.json()
        except Exception as e:
            print(f"Error fetching data for {mockupNameKey} page {page}: {e}")
            break
            
        items = data.get('data', [])
        if not items:
            print(f"[{mockupNameKey}] Empty data at page {page}. Finished.")
            break
            
        all_items.extend(items)
        
        # Filter items we already have
        new_items = []
        for item in items:
            num = str(item.get('num'))
            if num not in existing_nums:
                new_items.append(item)
                existing_nums.add(num)
                
        if not new_items:
            print(f"[{mockupNameKey}] Page {page} has 0 new items. Checking next page...")
            page += 1
            time.sleep(0.5)
            continue
            
        batch_data = []
        # Parallel image download for this page's NEW items
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_num = {}
            for item in new_items:
                num = str(item.get('num'))
                img_url = item.get('image')
                future = executor.submit(download_image, img_url, num)
                future_to_num[future] = item
                
            for future in concurrent.futures.as_completed(future_to_num):
                item = future_to_num[future]
                num = str(item.get('num'))
                try:
                    res_num, local_img = future.result()
                except Exception:
                    local_img = ""
                    
                # Serialize fields that are objects/lists
                cate_info = json.dumps(item.get('cate_info', {})) if isinstance(item.get('cate_info'), dict) else str(item.get('cate_info', ''))
                tags = json.dumps(item.get('tags', [])) if isinstance(item.get('tags'), list) else str(item.get('tags', ''))
                
                batch_data.append((
                    num,
                    item.get('mockupName', ''),
                    item.get('mockupNameKey', ''),
                    cat_info['class1'],
                    cat_info['class2Bymodel'],
                    item.get('keywords', ''),
                    item.get('modelKeywords', ''),
                    item.get('productKeywords', ''),
                    tags,
                    local_img if local_img else item.get('image', ''),
                    cate_info,
                    item.get('nameKey', '')
                ))

        with db_lock:
            try:
                conn.executemany('''
                    INSERT OR REPLACE INTO json_data 
                    (num, mockupName, mockupNameKey, class1, class2Bymodel, keywords, modelKeywords, productKeywords, tags, image, cate_info, nameKey) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', batch_data)
                conn.commit()
            except Exception as e:
                print(f"DB Insert error: {e}")
            
        print(f"[{mockupNameKey}] Processed page {page}")
        page += 1
        
    # Save the merged category to JSON
    json_path = os.path.join(JSON_DIR, f"{mockupNameKey}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_items, f, indent=2, ensure_ascii=False)
        
    print(f"Saved {len(all_items)} items for {mockupNameKey} to {json_path}")

def main():
    conn = init_db()
    
    # Load all existing nums into a set so we don't re-scrape/download them
    rows = conn.execute("SELECT num FROM json_data").fetchall()
    existing_nums = set(str(row[0]) for row in rows)
    print(f"Loaded {len(existing_nums)} existing items from database. Will skip scraping these.")
    
    categories = get_categories()
    print(f"Found {len(categories)} categories to scrape.")
    
    # We can parallelize across categories, but be careful of rate limits.
    # 5 workers seems reasonable.
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(scrape_category, cat, conn, existing_nums) for cat in categories]
        
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"Category scrape failed: {e}")
                
    conn.close()
    print("All scraping finished!")

if __name__ == '__main__':
    main()
