import sqlite3

c = sqlite3.connect('extracted_data.db')
rows = c.execute("SELECT cate_info FROM json_data WHERE num='600050'").fetchone()
print(rows)
