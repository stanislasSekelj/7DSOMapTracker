# Seven Deadly Sins: Origin - Interactive Live Map Tracker

A high-performance, real-time live map tracking application for **Seven Deadly Sins: Origin**. This project provides a transparent, dual-screen or alt-tab friendly companion map that automatically tracks your in-game character position and orientation while playing.

---

> [!CAUTION]
> ### 🛑 Important Anti-Cheat Disclaimer
> **This tool is 100% compliant with standard game Terms of Service and Anti-Cheat software.**
> 
> This architecture does **NOT** read from, write to, or inject code into the memory space of the game client. It does not modify game files, nor does it intercept network packets.
>
> **How it works:** It uses native Windows Desktop Window Manager (`DWM`) APIs to passively capture visual frames of the game's window buffer. It then uses Computer Vision (specifically OpenCV `SIFT` feature matching and `HSV` color filtering) to compare the minimap on your screen with a high-resolution map database. Essentially, it just "looks" at your screen just like your real eyes do.

---

## 🚀 Features

- **Live Tracking:** Real-time tracking of character map coordinates and directional gaze angle via Computer Vision.
- **Background Support:** Hooks seamlessly into DirectX window buffers—tracking continues flawlessly even if the game is minimized or obscured by other windows (e.g. Chrome/Discord)!
- **Hardware Agnostic:** Automatically handles any monitor resolution or UI scaling configurations.
- **Glassmorphic UI:** Modern frontend map powered by Leaflet, displaying thousands of interactable gathering, mining, and viewpoint nodes.
- **Persistent State:** Saves your map filtering/layer configurations locally so your interface remains perfectly structured between sessions.
- **Offline / Portable:** Works 100% locally with zero hot-linked assets or backend database calls required.

## 🛠️ Installation & Usage (For Users)

You do **not** need to install Python or understand code to run this.

1. Head to the **Releases** tab on the right side of this GitHub repository.
2. Download the latest `7DS_LiveTracker.exe` (or clone the repository and run `build.bat` to compile it yourself).
3. Double click the Application file.
4. An interactive transparent crosshair window will appear. **Click and drag a box** roughly over where the minimap is located in your game.
5. The tracking server will start in the background. Open your web browser to `http://localhost:8000` to magically see your live location!

## 🧑‍💻 Architecture (For Developers)

The pipeline is split into a robust producer-consumer architecture:

- **Backend (`scanner.py`)**: Uses `pywin32` hooks to fetch the live window frame matrix. OpenCV `cv2.SIFT_create()` extracts geometric landmarks from the minimap slice and matches them against the master `full_map.jpg` dataset via `FlannBasedMatcher`.
- **WebSocket Server (`main.py`)**: Streams the mapped `(x, y, angle)` coordinates out asynchronously over `wss://localhost:8765` so performance is isolated.
- **Frontend (`app.js`)**: A Leaflet map instances intercept the payload via WebSockets, rotating a fluid CSS marker smoothly over the custom map coordinate CRS system (`Lat = (mapY + 4608) / 9216 * 1000`).

## 🏆 Credits and Acknowledgements

- **Netmarble**: The core game framework, original visual assets, icon graphics, and map textures are Intellectual Property of Netmarble. Used strictly for fan/educational purposes.
- **[ZeroLuck.gg](https://zeroluck.gg)**: Massive appreciation to the ZeroLuck team for their intensive labor manually compiling and organizing the thousands of POI (Point of Interest) coordinates utilized in the JSON datasets in this repository. Ensure you check out their web-based tools!
