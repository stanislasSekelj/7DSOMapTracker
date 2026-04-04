echo Installing Requirements to Global Environment...
pip install mss opencv-python websockets pywin32 pyinstaller

echo Cleaning old builds...
rmdir /S /Q build
rmdir /S /Q dist

echo Building 7DS Origin Live Tracker Executable...
pyinstaller --noconfirm --onefile ^
  --paths "backend" ^
  --add-data "backend/full_map.jpg;." ^
  --add-data "frontend;frontend" ^
  --icon "NONE" ^
  --name "7DS_LiveTracker" ^
  main.py

echo.
echo ===========================================
echo Build Complete!
echo You can find your packaged executable in:
echo /dist/7DS_LiveTracker/7DS_LiveTracker.exe
echo ===========================================
pause
