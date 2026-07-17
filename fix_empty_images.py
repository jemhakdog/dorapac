import sqlite3
import json

c = sqlite3.connect('extracted_data.db')
rows = c.execute("SELECT num, image, cate_info FROM json_data").fetchall()

updated = 0
for row in rows:
    num = row[0]
    img = row[1]
    cate_info_str = row[2]
    
    if img and img.startswith('//'):
        continue
        
    try:
        cate_info = json.loads(cate_info_str)
    except:
        continue
        
    # If image is just a filename like '600050.png', we don't know the real URL.
    # Let's see if we can find it in size_options
    real_url = cate_info.get('image', '')
    if not real_url:
        sizes = cate_info.get('size_options', [])
        if sizes and isinstance(sizes, list) and len(sizes) > 0:
            real_url = sizes[0].get('previewImgPath', '')
            
    if real_url and real_url.startswith('//'):
        c.execute("UPDATE json_data SET image = ? WHERE num = ?", (real_url, num))
        updated += 1

c.commit()
print(f"Updated {updated} missing/broken image URLs in DB.")
