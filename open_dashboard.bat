@echo off
cd /d "%~dp0"
netstat -ano | findstr ":8765" | findstr "LISTENING" >nul
if %errorlevel%==0 (
  start "" "http://localhost:8765"
) else (
  .venv\Scripts\streamlit run app.py --server.port 8765
)
