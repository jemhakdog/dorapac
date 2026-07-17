import sqlite3

DB_NAME = 'extracted_data.db'

def main():
    print("Connecting to database...")
    conn = sqlite3.connect(DB_NAME)
    
    print("Adding index to 'num' column... (This should take less than a second)")
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_json_data_num ON json_data(num)")
        print("Index added successfully! Future updates will be instant.")
    except Exception as e:
        print(f"Error adding index: {e}")
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    main()
