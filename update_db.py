import os
import json
import sqlite3

DB_NAME = 'extracted_data.db'
JSON_DIR = 'data_dumps'

def main():
    conn = sqlite3.connect(DB_NAME)
    
    # Optional: we can create the table if it doesn't exist, but it exists
    
    json_files = [f for f in os.listdir(JSON_DIR) if f.endswith('.json')]
    total_inserted = 0
    
    for filename in json_files:
        filepath = os.path.join(JSON_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                items = json.load(f)
            except:
                continue
                
        batch_data = []
        for item in items:
            num = str(item.get('num'))
            cate_info = json.dumps(item.get('cate_info', {})) if isinstance(item.get('cate_info'), dict) else str(item.get('cate_info', ''))
            tags = json.dumps(item.get('tags', [])) if isinstance(item.get('tags'), list) else str(item.get('tags', ''))
            
            # Extract class1 and class2Bymodel from cate_info if possible, or just use what we have in the DB if it exists.
            # But the JSON from API doesn't have class1/class2Bymodel at top level unless we added it.
            # However, the user said they just finished scraping. Let's assume their JSON structure.
            cate_info_dict = item.get('cate_info', {})
            class2_name = item.get('class2Bymodel') # might be missing if raw API JSON
            class1_name = item.get('class1')
            
            # Try to infer class2Bymodel from ctree.json or just insert nulls and let app.py filter.
            # Wait, if they just finished scraping with my script, it has class1 and class2Bymodel already because my script added it before dumping to JSON?
            # Actually, in my scrape.py, I dumped `items` which were raw API data! So they don't have class1/class2Bymodel top level!
            
            # Let's fix that by looking up the category. 
            mockupNameKey = item.get('mockupNameKey')
            
            batch_data.append((
                num,
                item.get('mockupName', ''),
                item.get('mockupNameKey', ''),
                class1_name,
                class2_name,
                item.get('keywords', ''),
                item.get('modelKeywords', ''),
                item.get('productKeywords', ''),
                tags,
                item.get('image', ''),
                cate_info,
                item.get('nameKey', '')
            ))
            
        try:
            conn.executemany('''
                INSERT OR IGNORE INTO json_data 
                (num, mockupName, mockupNameKey, class1, class2Bymodel, keywords, modelKeywords, productKeywords, tags, image, cate_info, nameKey) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', batch_data)
            total_inserted += len(batch_data)
        except Exception as e:
            print(f"Error inserting {filename}: {e}")
            
    conn.commit()
    conn.close()
    
    print(f"Finished updating database. Processed {total_inserted} items from {len(json_files)} files.")

if __name__ == '__main__':
    main()
