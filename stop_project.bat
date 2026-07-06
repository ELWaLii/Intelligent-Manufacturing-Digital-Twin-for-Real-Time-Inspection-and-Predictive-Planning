@echo off
REM ═══════════════════════════════════════════════════════════════════════════
REM  KAVE Intelligent Manufacturing — Full Shutdown (Windows)
REM ═══════════════════════════════════════════════════════════════════════════

title KAVE Intelligent Manufacturing - Shutdown
color 4F

echo.
echo  ============================================================
echo   KAVE Intelligent Manufacturing - Shutdown Sequence
echo  ============================================================
echo.

echo [1/3] Stopping Python Scripts...
taskkill /FI "WINDOWTITLE eq KAVE_Producer*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq KAVE_Consumer*" /T /F >nul 2>&1
echo       Python processes terminated.
echo.

echo [2/3] Stopping Docker Containers...
docker compose down
echo       Docker containers stopped.
echo.

echo [3/3] Cleanup complete.
echo.
echo  ============================================================
echo   System completely shut down.
echo  ============================================================
echo.
pause
