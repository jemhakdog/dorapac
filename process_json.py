import os
import json
import sqlite3

directory = r"c:\Users\Administrator\Desktop\projects\dorapac\extracted_json"
db_path = r"c:\Users\Administrator\Desktop\projects\dorapac\extracted_data.db"

all_data = []
files_processed = 0

for filename in os.listdir(directory):
    if filename.endswith(".json"):
        file_path = os.path.join(directory, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
                
            data_val = content.get("data")
            
            if isinstance(data_val, list) and len(data_val) > 0:
                for item in data_val:
                    flat_item = {}
                    for k, v in item.items():
                        if isinstance(v, (dict, list)):
                            flat_item[k] = json.dumps(v, ensure_ascii=False)
                        else:
                            flat_item[k] = str(v) if v is not None else ""
                    flat_item['_source_file'] = filename
                    all_data.append(flat_item)
                files_processed += 1
        except Exception as e:
            print(f"Error reading {filename}: {e}")

if all_data:
    print(f"Found {len(all_data)} records across {files_processed} files. Saving to SQLite...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    columns = set()
    for item in all_data:
        columns.update(item.keys())
    
    columns = list(columns)
    
    col_defs = ", ".join([f'"{col}" TEXT' for col in columns])
    cursor.execute(f"CREATE TABLE IF NOT EXISTS json_data ({col_defs})")
    
    cursor.execute("DELETE FROM json_data")
    
    placeholders = ", ".join(["?" for _ in columns])
    col_str = ', '.join(['"' + c + '"' for c in columns])
    insert_sql = f"INSERT INTO json_data ({col_str}) VALUES ({placeholders})"
    
    for item in all_data:
        values = [item.get(col, "") for col in columns]
        cursor.execute(insert_sql, values)
        
    conn.commit()
    conn.close()
    print(f"Successfully saved to {db_path}")
else:
    print("No data found matching the criteria.")
