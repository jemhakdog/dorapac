import os
import json
import sqlite3

def main():
    print("Loading ctree.json...")
    with open('ctree.json', 'r', encoding='utf-8') as f:
        ctree_data = json.load(f)
        
    # Map category mockupNameKey to (class1, class2Bymodel)
    cat_map = {}
    for top_level in ctree_data.get('data', []):
        class1 = top_level.get('name')
        for child in top_level.get('children', []):
            mkey = child.get('mockupNameKey')
            name = child.get('name')
            if mkey and name and class1:
                cat_map[mkey] = (class1, name)
                
    conn = sqlite3.connect('extracted_data.db')
    cursor = conn.cursor()
    
    updates = 0
    missing = 0
    
    for filename in os.listdir('data_dumps'):
        if not filename.endswith('.json'):
            continue
            
        # The filename (without .json) is the exact category mockupNameKey
        cat_key = filename.replace('.json', '')
        
        if cat_key not in cat_map:
            # print(f"Warning: {cat_key} not found in ctree.json mapping.")
            continue
            
        class1, class2Bymodel = cat_map[cat_key]
        
        filepath = os.path.join('data_dumps', filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                items = json.load(f)
            except:
                continue
                
        # Update each item in the DB with the correct categories
        for item in items:
            num = str(item.get('num'))
            cursor.execute("UPDATE json_data SET class1 = ?, class2Bymodel = ? WHERE num = ?", (class1, class2Bymodel, num))
            if cursor.rowcount > 0:
                updates += cursor.rowcount
            else:
                missing += 1
                
    conn.commit()
    conn.close()
    print(f"Successfully fixed categories for {updates} items! ({missing} items were not in DB)")

if __name__ == '__main__':
    main()
