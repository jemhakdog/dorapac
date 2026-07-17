import sqlite3
c = sqlite3.connect('extracted_data.db')
row = c.execute("SELECT knife, modeSetting FROM json_data WHERE num='600050'").fetchone()
print(row)
