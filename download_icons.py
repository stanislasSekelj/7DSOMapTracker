import os
import json
import urllib.request
from urllib.parse import urlparse

# Define paths
JSON_DIR = "frontend/json/"
ICONS_DIR = "frontend/icons/"

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_basename(url):
    parsed = urlparse(url)
    return os.path.basename(parsed.path)

def main():
    ensure_dir(ICONS_DIR)
    
    # Track downloaded URLs so we don't redownload the same icon
    downloaded_urls = {}
    
    for filename in os.listdir(JSON_DIR):
        if not filename.endswith(".json"):
            continue
            
        filepath = os.path.join(JSON_DIR, filename)
        print(f"Scanning {filename}...")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"Error parsing {filename}")
                continue
                
        if "markers" not in data:
            print(f"No 'markers' array in {filename}")
            continue
            
        modified = False
        for marker in data["markers"]:
            # Check for both iconUrl and icon_url
            for key in ["iconUrl", "icon_url"]:
                if key in marker and marker[key]:
                    url = marker[key]
                    
                    if url.startswith("http"):
                        basename = get_basename(url)
                        local_path = f"icons/{basename}"
                        full_local_path = os.path.join(ICONS_DIR, basename)
                        
                        # Download if we haven't already
                        if url not in downloaded_urls:
                            if not os.path.exists(full_local_path):
                                print(f"Downloading {basename}...")
                                try:
                                    # Add User-Agent just in case their server blocks simple scripts
                                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                                    with urllib.request.urlopen(req, timeout=10) as response, open(full_local_path, 'wb') as out_file:
                                        out_file.write(response.read())
                                except Exception as e:
                                    print(f"Failed to download {url}: {e}")
                            downloaded_urls[url] = local_path
                            
                        # Replace URL with local path in JSON payload
                        marker[key] = local_path
                        modified = True
                        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            print(f"Updated {filename} with local icon paths.")

if __name__ == "__main__":
    main()
