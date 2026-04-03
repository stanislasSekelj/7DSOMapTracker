import cv2
import mss
import os
import sys
import numpy as np
import websockets
import asyncio
import json
import time
import win32gui
import win32ui
import win32con
import ctypes
import time
import mss
from selector import select_screen_area

# Configurable constants
DEFAULT_BOUNDING_BOX = {'top': 100, 'left': 1600, 'width': 300, 'height': 300} # Adjust based on your screen resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
FULL_MAP_PATH = os.path.join(current_dir, 'full_map.jpg')
UPDATE_FPS = 5

class MinimapScanner:
    def __init__(self, bounding_box=None):
        print("Initializing Scanner...")
        self.bounding_box = bounding_box if bounding_box else DEFAULT_BOUNDING_BOX
        
        # Convert to local paths incase we trigger pyinstaller later
        self.full_map = cv2.imread(FULL_MAP_PATH, cv2.IMREAD_COLOR)
        if self.full_map is None:
            raise FileNotFoundError(f"Could not load {FULL_MAP_PATH}. Ensure the image is in the backend directory.")

        # Save dimensions for reference
        self.map_h, self.map_w = self.full_map.shape[:2]

        # Use SIFT for rotation-invariant and scale-invariant matching
        # Removed nfeatures limit to allow detecting max possible features
        self.sift = cv2.SIFT_create()

        # CLAHE helps immensely with finding features in low-contrast/blurry maps
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))

        print("Computing keypoints for the full map... This may take a few seconds.")
        # Cache full map keypoints to save computing power
        self.map_gray = cv2.cvtColor(self.full_map, cv2.COLOR_BGR2GRAY)
        self.map_gray = self.clahe.apply(self.map_gray)
        self.kp_map, self.des_map = self.sift.detectAndCompute(self.map_gray, None)
        
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        self.flann = cv2.FlannBasedMatcher(index_params, search_params)

        self.last_pos = None

        # -----------------------------
        # WIN32 Window Capture Setup
        # -----------------------------
        self.hwnd = self._find_target_window("SevenDeadlySins")
        if not self.hwnd:
            self.hwnd = self._find_target_window("7DS")
            
        self.use_win32 = False
        if self.hwnd:
            self.use_win32 = True
            title = win32gui.GetWindowText(self.hwnd)
            print(f"Target Window Found: '{title}' (HWND: {self.hwnd}).")
            print("Switching to DWM active-buffer background capture.")
            
            # Convert screen absolute area to window client relative area
            client_pt = win32gui.ClientToScreen(self.hwnd, (0, 0))
            self.rel_box = {
                'left': max(0, self.bounding_box['left'] - client_pt[0]),
                'top': max(0, self.bounding_box['top'] - client_pt[1]),
                'width': self.bounding_box['width'],
                'height': self.bounding_box['height']
            }
        else:
            print("Target Window not found. Falling back to simple screen capture.")
            import mss
            self.sct = mss.mss()

    def _find_target_window(self, title_keyword):
        found_hwnd = None
        def enum_cb(hwnd, ctx):
            nonlocal found_hwnd
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title_keyword.lower() in title.lower():
                    found_hwnd = hwnd
        win32gui.EnumWindows(enum_cb, None)
        return found_hwnd

    def _capture_window_rect(self, hwnd, rel_box):
        try:
            left, top, right, bottom = win32gui.GetClientRect(hwnd)
        except Exception:
            return None
            
        w = right - left
        h = bottom - top
        if w <= 0 or h <= 0:
            return None

        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)
        
        # PW_CLIENTONLY | PW_RENDERFULLCONTENT (3) captures DirectX overlay buffers
        result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)
        
        img = None
        if result == 1:
            bmpstr = saveBitMap.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype='uint8')
            img.shape = (h, w, 4)
            
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)

        if img is not None:
            x1, y1 = rel_box['left'], rel_box['top']
            x2, y2 = x1 + rel_box['width'], y1 + rel_box['height']
            x2 = min(x2, w)
            y2 = min(y2, h)
            if x2 > x1 and y2 > y1:
                return img[y1:y2, x1:x2]
        return None

    def detect_arrow_angle(self, minimap_bgr):
        h, w = minimap_bgr.shape[:2]
        cy, cx = h//2, w//2
        r = int(w * 0.15) # Tight bounding box around center arrow
        center_crop = minimap_bgr[cy-r:cy+r, cx-r:cx+r]
        
        # Convert to HSV to rigidly isolate the pure Cyan/Blue glow of the player arrow
        # bypassing the white rocks and sand that break grayscale thresholding
        hsv = cv2.cvtColor(center_crop, cv2.COLOR_BGR2HSV)
        
        # Cyan hue in OpenCV is roughly 90 on a 0-180 scale
        lower_cyan = np.array([80, 100, 150])
        upper_cyan = np.array([110, 255, 255])
        thresh = cv2.inRange(hsv, lower_cyan, upper_cyan)
        
        # Close the hollow white core to make a solid geometric arrow blob
        kernel = np.ones((3,3), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return 0.0
            
        c = max(contours, key=cv2.contourArea)
        if cv2.contourArea(c) < 5:
            return 0.0
            
        # Find centroid
        M = cv2.moments(c)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
        else:
            return 0.0
            
        # The tip of the arrow is furthest from centroid
        max_dist = 0
        tip = (cX, cY)
        for pt in c:
            px, py = pt[0]
            dist = (px - cX)**2 + (py - cY)**2
            if dist > max_dist:
                max_dist = dist
                tip = (px, py)
                
        dx = tip[0] - cX
        dy = tip[1] - cY
        
        # 0 = Right, -90 = Top in typical CV pixel coords
        # Shift so Top is 0 for CSS rotate()
        angle = np.degrees(np.arctan2(dy, dx))
        return (angle + 90.0) % 360.0

    def scan(self):
        # 1. Capture screen region (where the minimap is)
        if getattr(self, 'use_win32', False):
            minimap = self._capture_window_rect(self.hwnd, self.rel_box)
            if minimap is None:
                return None
            minimap_bgr = cv2.cvtColor(minimap, cv2.COLOR_BGRA2BGR)
        else:
            screenshot = self.sct.grab(self.bounding_box)
            minimap = np.array(screenshot) # BGRA
            minimap_bgr = cv2.cvtColor(minimap, cv2.COLOR_BGRA2BGR)
        
        # Find player arrow rotation
        angle = self.detect_arrow_angle(minimap_bgr)
        
        minimap_gray = cv2.cvtColor(minimap_bgr, cv2.COLOR_BGR2GRAY)
        minimap_gray = self.clahe.apply(minimap_gray) # Boost contrast

        # 2. Apply a masking circle to exclude borders and outer UI
        h, w = minimap_gray.shape
        mask = np.zeros((h, w), dtype=np.uint8)
        # Exclude the very center (player arrow) and outer ring. 
        cv2.circle(mask, (w//2, h//2), int(w*0.42), 255, -1)
        cv2.circle(mask, (w//2, h//2), int(w*0.08), 0, -1)
        
        # 3. Detect keypoints on masked minimap
        kp_mini, des_mini = self.sift.detectAndCompute(minimap_gray, mask)

        if des_mini is None or len(des_mini) < 4:
            return None

        # 4. Try FAST LOCAL Tracking first
        if self.last_pos is not None:
            lx, ly = self.last_pos
            LOCAL_SEARCH_SIZE = 1200
            min_x = max(0, lx - LOCAL_SEARCH_SIZE // 2)
            max_x = min(self.map_w, lx + LOCAL_SEARCH_SIZE // 2)
            min_y = max(0, ly - LOCAL_SEARCH_SIZE // 2)
            max_y = min(self.map_h, ly + LOCAL_SEARCH_SIZE // 2)

            local_map = self.map_gray[min_y:max_y, min_x:max_x]
            kp_local, des_local = self.sift.detectAndCompute(local_map, None)

            if des_local is not None and len(des_local) > 10:
                # We can reuse flann directly
                matches = self.flann.knnMatch(des_mini, des_local, k=2)
                
                good_matches = []
                for m_tuple in matches:
                    if len(m_tuple) == 2:
                        m, n = m_tuple
                        if m.distance < 0.8 * n.distance:
                            good_matches.append(m)

                if len(good_matches) >= 6:
                    src_pts = np.float32([ kp_mini[m.queryIdx].pt for m in good_matches ]).reshape(-1, 1, 2)
                    dst_pts = np.float32([ kp_local[m.trainIdx].pt for m in good_matches ]).reshape(-1, 1, 2)

                    M, mask_ransac = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

                    if M is not None:
                        h_mini, w_mini = minimap_gray.shape
                        pts = np.float32([ [w_mini/2, h_mini/2] ]).reshape(-1, 1, 2)
                        dst = cv2.perspectiveTransform(pts, M)
                        
                        center_x = int(dst[0][0][0]) + min_x
                        center_y = int(dst[0][0][1]) + min_y

                        dist = np.sqrt((center_x - self.last_pos[0])**2 + (center_y - self.last_pos[1])**2)
                        if dist < 400: # Slightly relaxed distance for running
                            center_x = int(0.3 * center_x + 0.7 * self.last_pos[0])
                            center_y = int(0.3 * center_y + 0.7 * self.last_pos[1])
                            self.last_pos = (center_x, center_y)
                            return center_x / self.map_w, center_y / self.map_h, angle

            # If tracking fails, reset last_pos to trigger global fallback
            self.last_pos = None

        # 5. GLOBAL MATCHING FALLBACK (If lost or initializing)
        matches = self.flann.knnMatch(des_mini, self.des_map, k=2)

        # Apply Lowe's ratio test to filter false matches
        good_matches = []
        for m_tuple in matches:
            if len(m_tuple) == 2:
                m, n = m_tuple
                if m.distance < 0.8 * n.distance:
                    good_matches.append(m)

        if len(good_matches) >= 6: 
            src_pts = np.float32([ kp_mini[m.queryIdx].pt for m in good_matches ]).reshape(-1, 1, 2)
            dst_pts = np.float32([ self.kp_map[m.trainIdx].pt for m in good_matches ]).reshape(-1, 1, 2)

            M, mask_ransac = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

            if M is not None:
                h_mini, w_mini = minimap_gray.shape
                pts = np.float32([ [w_mini/2, h_mini/2] ]).reshape(-1, 1, 2)
                dst = cv2.perspectiveTransform(pts, M)
                
                center_x = int(dst[0][0][0])
                center_y = int(dst[0][0][1])

                self.last_pos = (center_x, center_y)
                return center_x / self.map_w, center_y / self.map_h, angle
        
        return None

async def broadcast_location(websocket, path=None):
    print("Client connected to map tracker!")
    try:
        while True:
            start_time = time.time()
            pos = scanner_instance.scan()
            if pos:
                x_pct, y_pct, angle = pos
                print(f"Location updated: X%={x_pct:.4f}, Y%={y_pct:.4f}, Angle={angle:.1f}")
                await websocket.send(json.dumps({'x_pct': x_pct, 'y_pct': y_pct, 'angle': angle, 'found': True}))
            else:
                await websocket.send(json.dumps({'found': False}))
            
            elapsed = time.time() - start_time
            await asyncio.sleep(max(0, (1.0 / UPDATE_FPS) - elapsed))
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected.")

async def main():
    print("Back-end ready! Starting WebSocket server on ws://localhost:8765")
    async with websockets.serve(broadcast_location, "localhost", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    print("Launching UI selector... check your screen!")
    area = select_screen_area()
    if area:
        print(f"Using selected screen area: {area}")
    else:
        print("No area selected, using default bounding box.")
        
    scanner_instance = MinimapScanner(area)
    asyncio.run(main())
