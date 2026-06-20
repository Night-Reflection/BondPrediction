@echo off
echo Starting PostgreSQL Docker container...
docker compose up -d

echo Waiting for database to wake up...
:wait_loop
docker exec prediction_db_container pg_isready -U admin -d market_predictions >nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

echo Database is ready!
echo Launching prediction application...
python run.py
pause