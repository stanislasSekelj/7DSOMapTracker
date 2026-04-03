import re
import urllib.request
import os
import cv2
import numpy as np
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

def main():
    print("Analyzing sourcecode...")
    try:
        with open(r'd:\Personal Project\7DSMAP\sourcecode', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print("Error reading sourcecode:", e)
        return

    import re
    # We will search for literal URLs in the escaped JSON string.
    # We find things like: T_UI_WM_Splitted_Britannia_World_0_0-12345.png
    # But let's just find the exact url strings. They will be prefixed by \"url\":\" and end with .png\"
    pattern = re.compile(r'\\(?:")url\\(?:"):\\(?:")(https://zeroluck\.gg/[^\\]+/T_UI_WM_Splitted_[a-zA-Z_]+_(\d+)_(\d+)-\d+\.png)\\?(?:")')
    
    # Wait, the backslashes might be escaping the quotes. So it's \\"url\\":\\"http...png\\"
    # Or we can just grab all png strings from zeroluck.gg that look like tiles:
    pattern_fallback = re.compile(r'(https://zeroluck\.gg[a-zA-Z0-9_/\.-]+/T_UI_WM_Splitted_[a-zA-Z_]+_(\d+)_(\d+)-\d+\.png)')
    
    raw_matches = pattern_fallback.findall(content)
    
    # `raw_matches` will be a list of tuples: (url, x, y)
    # We just need to map them back to x, y, url
    matches = [(m[1], m[2], m[0]) for m in raw_matches]
    
    # Deduplicate because there might be multiple occurrences in the page source
    matches = list(set(matches))
    
    if not matches:
        print("No tiles found in the source text! Generating debug output of 1000 chars:")
        print(content[:1000])
        return
        
    print(f"Found {len(matches)} tile descriptors.")
    
    # Determine the complete grid size
    # In the JSON, cols=18, rows=18
    cols = max(int(m[0]) for m in matches) + 1
    rows = max(int(m[1]) for m in matches) + 1
    
    T_SIZE = 512
    width = cols * T_SIZE
    height = rows * T_SIZE
    
    print(f"Map size will be {width}x{height} pixels ({cols}x{rows} tiles)")
    print("Downloading and stitching tiles... this will take a minute or two.")
    
    map_img = np.zeros((height, width, 3), dtype=np.uint8)
    
    for idx, (x_str, y_str, url) in enumerate(matches):
        x = int(x_str)
        y = int(y_str)
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        try:
            resp = urllib.request.urlopen(req)
            img_array = np.asarray(bytearray(resp.read()), dtype=np.uint8)
            tile = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if tile is not None:
                # The site might map origin at top-left. Let's assume standard image mapping.
                map_img[y*T_SIZE:(y+1)*T_SIZE, x*T_SIZE:(x+1)*T_SIZE] = tile
                if idx % 20 == 0:
                    print(f"Progress: {idx}/{len(matches)} tiles stitched...")
        except Exception as e:
            print(f"Failed to download tile {x},{y} from {url}: {e}")
            
    print("Done stitching! Saving map...")
    
    # We will save the massive one for the backend to use for precise SIFT matching
    # But since 9216x9216 is HUGE for both Vite and memory, let's output it as the primary map
    cv2.imwrite(r'd:\Personal Project\7DSMAP\backend\full_map.jpg', map_img)
    
    # Also overwrite the frontend one
    cv2.imwrite(r'd:\Personal Project\7DSMAP\frontend\assets\full_map.jpg', map_img)
    
    print("High-quality map successfully extracted and installed!")

if __name__ == '__main__':
    main()
