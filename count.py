import sqlite3

conn = sqlite3.connect('extracted_data.db')
tags = ['Soda Can', 'Beer Can', 'Energy Drink', 'Juice Can', 'Aluminum Can', 'Food Can', 'Oil Can', 'Coffee Can', 'Spray Can']

for t in tags:
    count = conn.execute("SELECT COUNT(*) FROM json_data WHERE tags LIKE ? OR keywords LIKE ?", (f"%{t}%", f"%{t}%")).fetchone()[0]
    print(f"{t}: {count}")
