import sqlite3
import os
import requests
import time
from urllib.parse import urlparse
import concurrent.futures
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

DB_NAME = 'extracted_data.db'
IMAGES_DIR = 'images'

os.makedirs(IMAGES_DIR, exist_ok=True)

# Configure a session with automatic retries for robust downloading
session = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries, pool_connections=100, pool_maxsize=100))
session.mount('http://', HTTPAdapter(max_retries=retries, pool_connections=100, pool_maxsize=100))

def download_image(url, item_num, attempt=1):
    if not url:
        return item_num, url, ""
    
    if not url.startswith("http") and not url.startswith("//"):
        filepath = os.path.join(IMAGES_DIR, str(item_num), url)
        if os.path.exists(filepath):
            return item_num, url, url
            
    original_url = url
    if url.startswith("//"):
        url = "https:" + url
        
    ext = os.path.splitext(urlparse(url).path)[1]
    if not ext:
        ext = '.png'
        
    filename = url.split('/')[-1] if '/' in url else f"{item_num}{ext}"
    
    img_dir = os.path.join(IMAGES_DIR, str(item_num))
    os.makedirs(img_dir, exist_ok=True)
    filepath = os.path.join(img_dir, filename)
    
    if os.path.exists(filepath):
        return item_num, original_url, filename
        
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Increased timeout to 30 seconds to prevent read timeouts on large images
        r = session.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(r.content)
            return item_num, original_url, filename
    except Exception as e:
        if attempt <= 3:
            # Simple exponential backoff for custom exceptions like read timeouts
            time.sleep(2 * attempt)
            return download_image(original_url, item_num, attempt + 1)
        else:
            print(f"Failed to download {item_num} after 3 attempts: {e}")
        
    return item_num, original_url, ""

def main():
    conn = sqlite3.connect(DB_NAME)
    rows = conn.execute("SELECT num, image FROM json_data WHERE image IS NOT NULL AND image != ''").fetchall()
    
    to_download = []
    for num, img in rows:
        if not img.startswith('http') and not img.startswith('//'):
            if not os.path.exists(os.path.join(IMAGES_DIR, str(num), img)):
                pass
        else:
            filename = img.split('/')[-1] if '/' in img else f"{num}.png"
            if not os.path.exists(os.path.join(IMAGES_DIR, str(num), filename)):
                to_download.append((num, img))
            else:
                to_download.append((num, img))
            
    print(f"Found {len(to_download)} items with URLs to verify/download.")
    
    updates = []
    # Reduced max_workers to 50 to prevent saturating bandwidth/router and getting timed out
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        future_to_num = {executor.submit(download_image, img, num): num for num, img in to_download}
        
        count = 0
        for future in concurrent.futures.as_completed(future_to_num):
            num = future_to_num[future]
            try:
                res_num, orig_url, local_img = future.result()
                if local_img and local_img != orig_url:
                    updates.append((local_img, res_num))
            except Exception:
                pass
                
            count += 1
            if count % 100 == 0:
                print(f"Processed {count}/{len(to_download)} images... (Will update {len(updates)} rows)")
                
    if updates:
        print(f"Updating {len(updates)} rows in DB to use local filenames...")
        conn.executemany("UPDATE json_data SET image = ? WHERE num = ?", updates)
        conn.commit()
        
    conn.close()
    print("Done checking and downloading missing images.")

if __name__ == '__main__':
    main()
