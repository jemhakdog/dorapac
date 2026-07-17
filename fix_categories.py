import json
import sqlite3

def main():
    print("Loading ctree.json...")
    with open('ctree.json', 'r', encoding='utf-8') as f:
        ctree_data = json.load(f)
        
    # Map mockupNameKey to the correct frontend category name
    key_to_name = {}
    for top_level in ctree_data.get('data', []):
        for child in top_level.get('children', []):
            mkey = child.get('mockupNameKey')
            name = child.get('name')
            if mkey and name:
                key_to_name[mkey] = name
                
    print(f"Found {len(key_to_name)} category mappings.")
    
    print("Updating database...")
    conn = sqlite3.connect('extracted_data.db')
    cursor = conn.cursor()
    
    updates = 0
    for mkey, correct_name in key_to_name.items():
        cursor.execute("UPDATE json_data SET class2Bymodel = ? WHERE mockupNameKey = ?", (correct_name, mkey))
        updates += cursor.rowcount
        
    conn.commit()
    conn.close()
    
    print(f"Successfully updated {updates} items with their correct frontend categories!")

if __name__ == '__main__':
    main()
