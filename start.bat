@echo off
echo ================================================
echo   India Beauty Biz Scraper - Starting Servers
echo ================================================
echo.
echo [1/2] Starting REST API on http://localhost:8000
echo       API Docs: http://localhost:8000/docs
start "API Server" cmd /k "cd /d "%~dp0" && uvicorn api:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 2 /nobreak >nul

echo [2/2] Starting Streamlit UI on http://localhost:8501
start "Streamlit UI" cmd /k "cd /d "%~dp0" && streamlit run app.py"

echo.
echo Both servers are starting...
echo   Streamlit UI  → http://localhost:8501
echo   REST API      → http://localhost:8000
echo   API Docs      → http://localhost:8000/docs
echo.
pause
