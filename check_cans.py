import sqlite3
c = sqlite3.connect('extracted_data.db')
c.row_factory = sqlite3.Row
cat_rows = c.execute("SELECT class1, class2Bymodel, COUNT(*) as cnt FROM json_data GROUP BY class1, class2Bymodel").fetchall()
for r in cat_rows:
    if r['class1'] == 'Cans':
        print(r['class2Bymodel'], r['cnt'])
