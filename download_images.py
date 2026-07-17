import os
import json
import asyncio
import aiohttp
from pathlib import Path
from urllib.parse import urlparse

async def download_image(session, url, folder_path, semaphore):
    # Fix protocol-relative URLs
    if url.startswith('//'):
        url = 'https:' + url
    
    if not url.startswith('http'):
        return # Skip invalid URLs
    
    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)
    if not filename:
        filename = "image.png"
        
    file_path = folder_path / filename
    
    if file_path.exists():
        return # Already downloaded
    
    async with semaphore:
        try:
            async with session.get(url, timeout=15) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    print(f"Downloaded: {filename} to {folder_path.name}")
                else:
                    print(f"Failed to download {url}: HTTP {response.status}")
        except Exception as e:
            print(f"Error downloading {url}: {e}")

async def main():
    json_dir = Path('extracted_json')
    images_dir = Path('images')
    images_dir.mkdir(exist_ok=True)
    
    if not json_dir.exists():
        print("Directory extracted_json does not exist!")
        return

    tasks = []
    semaphore = asyncio.Semaphore(50) # Limit concurrent downloads
    
    async with aiohttp.ClientSession() as session:
        for json_file in json_dir.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                items = data.get('data', [])
                if not isinstance(items, list):
                    continue
                    
                for item in items:
                    item_id = item.get('id')
                    if not item_id:
                        continue
                        
                    folder_path = images_dir / str(item_id)
                    folder_path.mkdir(exist_ok=True)
                    
                    # Collect all image URLs for this item
                    urls = set()
                    
                    if item.get('image'):
                        urls.add(item.get('image'))
                    if item.get('knife'):
                        urls.add(item.get('knife'))
                        
                    cate_info = item.get('cate_info', {})
                    if isinstance(cate_info, dict) and cate_info.get('image'):
                        urls.add(cate_info.get('image'))
                        
                    for mode in item.get('modeSetting', []):
                        if isinstance(mode, dict) and mode.get('image'):
                            urls.add(mode.get('image'))
                            
                    for url in urls:
                        if url:
                            tasks.append(download_image(session, url, folder_path, semaphore))
                            
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                
        print(f"Starting {len(tasks)} image downloads...")
        await asyncio.gather(*tasks)
        print("All downloads completed!")

if __name__ == '__main__':
    asyncio.run(main())
