import sqlite3
c=sqlite3.connect('extracted_data.db')
for row in c.execute('SELECT mockupNameKey, class2Bymodel, COUNT(*) FROM json_data WHERE mockupNameKey LIKE "%tube%" GROUP BY mockupNameKey, class2Bymodel').fetchall():
    print(row)
