@echo off
cd /d "%~dp0"
docker compose up --build -d
echo ---
echo Waiting 30 seconds for services to start...
timeout /t 30 /nobreak >nul
echo ---
echo === API LOGS ===
docker compose logs api --tail=30
echo ---
echo === FRONTEND LOGS ===
docker compose logs frontend --tail=15
echo ---
echo === HEALTH CHECK ===
curl -s http://localhost:8000/health
echo.
echo ---
echo === CONTAINER STATUS ===
docker compose ps
