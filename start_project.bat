@echo off
REM ═══════════════════════════════════════════════════════════════════════════
REM  KAVE Intelligent Manufacturing — One-Click Launcher (Windows)
REM ═══════════════════════════════════════════════════════════════════════════
REM  This script will:
REM    1. Start Docker infrastructure (Kafka, DBs, Grafana, Redis, AI)
REM    2. Wait for Kafka and databases to initialize
REM    3. Launch Sensor Producer in a named terminal
REM    4. Launch Sensor Consumer in a named terminal
REM    5. Open the Streamlit dashboard in the browser
REM ═══════════════════════════════════════════════════════════════════════════

title KAVE Intelligent Manufacturing - Launcher
color 1F

echo.
echo  ============================================================
echo   KAVE Intelligent Manufacturing - Enterprise Launcher
echo  ============================================================
echo.

REM ── Step 1: Check Docker ─────────────────────────────────────────────────
echo [1/5] Checking Docker availability...
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: Docker is not running!
    echo  Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)
echo       Docker is running.
echo.

REM ── Step 2: Start Docker Infrastructure ──────────────────────────────────
echo [2/5] Starting KAVE Docker Infrastructure...
echo.
docker compose up -d
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: Docker Compose failed to start!
    echo  Check the logs with: docker compose logs
    echo.
    pause
    exit /b 1
)
echo.
echo       All containers started successfully.
echo.

REM ── Step 3: Wait for Kafka and Databases ─────────────────────────────────
echo [3/5] Waiting for Kafka and Databases to initialize...
timeout /t 15 >nul
echo       Initialization window complete.
echo.

REM ── Step 4: Launch Producer & Consumer ───────────────────────────────────
echo [4/5] Starting Sensor Producer and Consumer...
start "KAVE_Producer" cmd /k "cd /d %~dp0data-processing\iot_sensor_sim && py sensor_producer.py"
start "KAVE_Consumer" cmd /k "cd /d %~dp0data-processing\streaming_consumers && py sensor_consumer.py"
echo       Producer and Consumer launched in separate terminals.
echo.

REM ── Step 5: Open Dashboard ───────────────────────────────────────────────
echo [5/5] Opening KAVE Dashboard...
echo.
start http://localhost:8501
echo.
echo  ============================================================
echo   KAVE Manufacturing Platform is LIVE!
echo  ============================================================
echo.
echo   Dashboard:  http://localhost:8501
echo   Vision API: http://localhost:8000
echo   Grafana:    http://localhost:3000
echo   Kafka:      localhost:9092
echo   PostgreSQL: localhost:5432
echo   InfluxDB:   localhost:8089
echo   Redis:      localhost:6379
echo.
echo   To stop:    run stop_project.bat
echo   To logs:    docker compose logs -f
echo  ============================================================
echo.
echo System is fully running!
pause
