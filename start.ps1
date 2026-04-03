Write-Host "Starting 7DS Origin Live Tracker..." -ForegroundColor Cyan

# Start the frontend Vanilla Server
Write-Host "Starting frontend server on http://localhost:8000" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'frontend'; python -m http.server 8000"

# Start the Python Scanner service
Write-Host "Starting backend scanner..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'backend'; .\venv\Scripts\Activate.ps1; python scanner.py"

Write-Host "Done! Please open your browser to http://localhost:8000 to see the tracker UI." -ForegroundColor Yellow
Write-Host "Make sure the game is running on your primary monitor." -ForegroundColor Yellow
