import json
import os

har_file = 'www.pacdora.com.allmodels.har'
output_dir = 'extracted_json'

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

print("Loading HAR file...")
with open(har_file, 'r', encoding='utf-8') as f:
    har_data = json.load(f)

count = 0
for entry in har_data['log']['entries']:
    url = entry['request']['url']
    # Based on the image, we want requests related to "models"
    if 'models?' in url or '/models' in url:
        response = entry.get('response', {})
        content = response.get('content', {})
        text = content.get('text')
        
        if text:
            # Try to parse and pretty print, but fallback to raw text if not JSON
            filename = os.path.join(output_dir, f'model_response_{count}.json')
            try:
                # If it's valid JSON, write it formatted
                parsed = json.loads(text)
                with open(filename, 'w', encoding='utf-8') as out_f:
                    json.dump(parsed, out_f, indent=2)
            except Exception:
                # Otherwise write raw text
                with open(filename, 'w', encoding='utf-8') as out_f:
                    out_f.write(text)
            count += 1

print(f"Extracted {count} JSON files to {output_dir}/")
