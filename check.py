import sqlite3
import json

conn = sqlite3.connect('extracted_data.db')
conn.row_factory = sqlite3.Row

r = conn.execute("SELECT mockupName, tags, keywords, modelKeywords, productKeywords, class2Bymodel FROM json_data WHERE num='601430'").fetchone()

if r:
    print(dict(r))
else:
    print('Not found')
