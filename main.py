import os
import sys
import threading
import http.server
import socketserver
import asyncio
import time

def get_base_path():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.abspath(os.path.dirname(__file__))

backend_path = os.path.join(get_base_path(), 'backend')
sys.path.insert(0, backend_path)

import scanner
import selector
import mss
import cv2

def start_http_server():
    import functools
    frontend_dir = os.path.join(get_base_path(), 'frontend')
    
    # Quiet the HTTP Server logs and explicitly bind to frontend dir
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass
            
    Handler = functools.partial(QuietHandler, directory=frontend_dir)
    try:
        httpd = socketserver.TCPServer(("", 8000), Handler)
        print("Frontend Server running on http://localhost:8000")
        httpd.serve_forever()
    except OSError:
        print("Port 8000 is occupied. The frontend might already be running.")
        pass

if __name__ == '__main__':
    print("========================================")
    print("         7DS Origin Live Tracker        ")
    print("========================================\n")
    
    # Start the frontend server as a daemon thread
    server_thread = threading.Thread(target=start_http_server, daemon=True)
    server_thread.start()
    
    # Give the server a moment to spin up
    time.sleep(1.0)
    
    try:
        import webbrowser
        webbrowser.open("http://localhost:8000")
    except Exception as e:
        print(f"Could not automatically open browser: {e}")
    
    # Launch tracking loop
    try:
        print("Launching UI selector... please draw a box over where your minimap is!")
        area = selector.select_screen_area()
        if area:
            print(f"Area selected. Starting backend loop...")
        else:
            print("No area selected. Falling back to default top-right corner.")
            
        scanner.scanner_instance = scanner.MinimapScanner(area)
        asyncio.run(scanner.main())
    except KeyboardInterrupt:
        print("Tracker closed.")
    except Exception as e:
        print(f"Fatal error: {e}")
        input("Press ENTER to exit...")
