import os
import json
import sqlite3
import math
from flask import Flask, render_template, request

app = Flask(__name__)

DB_PATH = 'extracted_data.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def dict_from_row(row):
    d = dict(row)
    for k, v in d.items():
        if v and isinstance(v, str) and (v.startswith('[') or v.startswith('{')):
            try:
                d[k] = json.loads(v)
            except json.JSONDecodeError:
                pass
    return d

@app.route('/')
def index():
    conn = get_db()
    # Load CATEGORY_MAPPING dynamically from ctree.json
    CATEGORY_MAPPING = {}
    try:
        with open('ctree.json', 'r', encoding='utf-8') as f:
            ctree_data = json.load(f)
            for top_level in ctree_data.get('data', []):
                parent_name = top_level.get('name')
                children = [child.get('name').strip() for child in top_level.get('children', []) if child.get('name')]
                if parent_name and children:
                    CATEGORY_MAPPING[parent_name] = children
                    
    except Exception as e:
        print("Error loading ctree.json:", e)

    # Get categories and counts using both class1 (parent) and class2Bymodel (child)
    cat_rows = conn.execute("SELECT class1, class2Bymodel, COUNT(*) as cnt FROM json_data GROUP BY class1, class2Bymodel").fetchall()
    
    # Group categories
    grouped_categories = {k: {} for k in CATEGORY_MAPPING.keys()}
    grouped_categories['Others'] = {}
    
    total_overall = 0
    
    for row in cat_rows:
        parent = row['class1']
        cat = row['class2Bymodel'].strip() if row['class2Bymodel'] else 'Other'
        cnt = row['cnt']
        
        total_overall += cnt
        
        if parent in grouped_categories:
            grouped_categories[parent][cat] = grouped_categories[parent].get(cat, 0) + cnt
        else:
            # Fallback if class1 isn't in CATEGORY_MAPPING
            found = False
            for p, children in CATEGORY_MAPPING.items():
                if cat in children:
                    grouped_categories[p][cat] = grouped_categories[p].get(cat, 0) + cnt
                    found = True
                    break
            if not found:
                grouped_categories['Others'][cat] = grouped_categories['Others'].get(cat, 0) + cnt
        
    # Remove empty groups
    grouped_categories = {k: v for k, v in grouped_categories.items() if v}
        

    
    # Filtering
    selected_parent_category = request.args.get('parent_category')
    selected_category = request.args.get('category')
    search_query = request.args.get('q', '').strip()
    view_type = request.args.get('type', 'mockups')
    
    # Pagination
    page = int(request.args.get('page', 1))
    per_page = 12
    offset = (page - 1) * per_page
    
    query_conditions = []
    query_params = []
    
    if selected_category:
        if selected_category == 'Other':
            query_conditions.append("(class2Bymodel IS NULL OR class2Bymodel = '')")
        else:
            query_conditions.append("class2Bymodel = ?")
            query_params.append(selected_category)
            if selected_parent_category:
                query_conditions.append("class1 = ?")
                query_params.append(selected_parent_category)
                
    elif selected_parent_category:
        query_conditions.append("class1 = ?")
        query_params.append(selected_parent_category)
            
    if search_query:
        query_conditions.append("mockupName LIKE ?")
        search_term = f"%{search_query}%"
        query_params.append(search_term)
        
    if view_type == 'dielines':
        query_conditions.append("knife IS NOT NULL AND knife != ''")
    elif view_type == '3d':
        query_conditions.append("cate_info LIKE '%pdaFile%'")
        
    where_clause = ""
    if query_conditions:
        where_clause = " WHERE " + " AND ".join(query_conditions)
        
    count_query = f"SELECT COUNT(*) FROM json_data{where_clause}"
    query = f"SELECT * FROM json_data{where_clause} LIMIT ? OFFSET ?"
    
    total_filtered = conn.execute(count_query, query_params).fetchone()[0]
    total_pages = math.ceil(total_filtered / per_page) if total_filtered > 0 else 1
    
    # Generate page window
    page_window = []
    if total_pages <= 7:
        page_window = list(range(1, total_pages + 1))
    else:
        if page <= 4:
            page_window = [1, 2, 3, 4, 5, None, total_pages]
        elif page >= total_pages - 3:
            page_window = [1, None, total_pages - 4, total_pages - 3, total_pages - 2, total_pages - 1, total_pages]
        else:
            page_window = [1, None, page - 1, page, page + 1, None, total_pages]
    
    query_params.extend([per_page, offset])
    items_rows = conn.execute(query, query_params).fetchall()
    paginated_items = [dict_from_row(row) for row in items_rows]
    
    conn.close()
    
    return render_template('index.html', 
                           items=paginated_items, 
                           grouped_categories=grouped_categories, 
                           total_items=total_overall,
                           selected_category=selected_category,
                           selected_parent_category=selected_parent_category,
                           search_query=search_query,
                           view_type=view_type,
                           page=page,
                           total_pages=total_pages,
                           page_window=page_window)

@app.route('/product/<num>')
def product(num):
    conn = get_db()
    row = conn.execute("SELECT * FROM json_data WHERE num = ?", (num,)).fetchone()
    conn.close()
    
    if not row:
        return "Product not found", 404
        
    product_data = dict_from_row(row)
    return render_template('product.html', product=product_data)

@app.route('/images/<num>/<path:filename>')
def serve_image(num, filename):
    import urllib.request
    from flask import send_from_directory
    
    img_dir = os.path.join(app.root_path, 'images', num)
    img_path = os.path.join(img_dir, filename)
    
    if os.path.exists(img_path):
        return send_from_directory(img_dir, filename)
        
    conn = get_db()
    row = conn.execute("SELECT image, knife, cate_info, modeSetting FROM json_data WHERE num = ?", (num,)).fetchone()
    conn.close()
    
    target_url = None
    if row:
        item = dict_from_row(row)
        possible_urls = []
        if item.get('image'):
            possible_urls.append(item.get('image'))
        if item.get('knife'):
            possible_urls.append(item.get('knife'))
        if item.get('cate_info'):
            if item['cate_info'].get('image'):
                possible_urls.append(item['cate_info'].get('image'))
            if item['cate_info'].get('size_options'):
                for size_opt in item['cate_info']['size_options']:
                    if size_opt.get('previewImgPath'):
                        possible_urls.append(size_opt.get('previewImgPath'))
        
        if item.get('modeSetting'):
            for mode in item['modeSetting']:
                if mode.get('image'):
                    possible_urls.append(mode.get('image'))
                    
        for url in possible_urls:
            if url.split('/')[-1] == filename:
                target_url = url
                break
                
    if target_url:
        if target_url.startswith('//'):
            target_url = 'https:' + target_url
            
        try:
            os.makedirs(img_dir, exist_ok=True)
            req = urllib.request.Request(target_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response, open(img_path, 'wb') as out_file:
                out_file.write(response.read())
            return send_from_directory(img_dir, filename)
        except Exception as ex:
            print(f"Error downloading {target_url}: {ex}")
            
    return "Not Found", 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)
