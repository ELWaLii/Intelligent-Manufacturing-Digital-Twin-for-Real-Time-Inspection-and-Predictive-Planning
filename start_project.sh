#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
#  KAVE Intelligent Manufacturing — One-Click Project Launcher (Linux/Mac)
# ═══════════════════════════════════════════════════════════════════════════════
#  This script will:
#    1. Verify Docker is running
#    2. Clean up old containers and volumes
#    3. Build and start all services
#    4. Wait for services to become healthy
#    5. Open the dashboard in your default browser
# ═══════════════════════════════════════════════════════════════════════════════

set -e

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo ""
echo -e "${BLUE}${BOLD} ============================================================${NC}"
echo -e "${BLUE}${BOLD}  KAVE Intelligent Manufacturing - Enterprise Launcher${NC}"
echo -e "${BLUE}${BOLD} ============================================================${NC}"
echo ""

# ── Step 1: Check Docker ─────────────────────────────────────────────────────
echo -e "${CYAN}[1/5]${NC} Checking Docker availability..."
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}  ERROR: Docker is not running!${NC}"
    echo "  Please start Docker and try again."
    exit 1
fi
echo -e "${GREEN}      ✅ Docker is running.${NC}"
echo ""

# ── Step 2: Cleanup ──────────────────────────────────────────────────────────
echo -e "${CYAN}[2/5]${NC} Cleaning up old containers..."
docker compose down --remove-orphans 2>/dev/null || true
echo -e "${GREEN}      ✅ Cleanup complete.${NC}"
echo ""

# ── Step 3: Build and Start ──────────────────────────────────────────────────
echo -e "${CYAN}[3/5]${NC} Building and starting all services (this may take a few minutes)..."
echo ""
docker compose up -d --build
echo ""
echo -e "${GREEN}      ✅ All containers started.${NC}"
echo ""

# ── Step 4: Wait for Services ────────────────────────────────────────────────
echo -e "${CYAN}[4/5]${NC} Waiting for services to become healthy..."
echo ""

MAX_WAIT=120
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Check if Streamlit dashboard is responding
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/_stcore/health 2>/dev/null || echo "000")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}      ✅ Dashboard is ready!${NC}"
        break
    fi
    
    echo "      Waiting... (${ELAPSED}s / ${MAX_WAIT}s)"
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "${YELLOW}      ⚠️  Some services may not be fully ready yet.${NC}"
    echo "      Check status with: docker compose ps"
fi
echo ""

# ── Step 5: Open Browser ─────────────────────────────────────────────────────
echo -e "${CYAN}[5/5]${NC} Opening KAVE Dashboard in your browser..."
echo ""

# Cross-platform browser open
if command -v xdg-open > /dev/null 2>&1; then
    xdg-open http://localhost:8501 &
elif command -v open > /dev/null 2>&1; then
    open http://localhost:8501 &
else
    echo "  Please open http://localhost:8501 in your browser."
fi

echo -e "${BLUE}${BOLD} ============================================================${NC}"
echo -e "${GREEN}${BOLD}  KAVE Manufacturing Platform is LIVE!${NC}"
echo -e "${BLUE}${BOLD} ============================================================${NC}"
echo ""
echo -e "  ${BOLD}Dashboard:${NC}  http://localhost:8501"
echo -e "  ${BOLD}Vision API:${NC} http://localhost:8000"
echo -e "  ${BOLD}Grafana:${NC}    http://localhost:3000"
echo -e "  ${BOLD}PostgreSQL:${NC} localhost:5432"
echo -e "  ${BOLD}Redis:${NC}      localhost:6379"
echo ""
echo -e "  To stop:    ${CYAN}docker compose down${NC}"
echo -e "  To logs:    ${CYAN}docker compose logs -f${NC}"
echo -e "${BLUE}${BOLD} ============================================================${NC}"
echo ""
