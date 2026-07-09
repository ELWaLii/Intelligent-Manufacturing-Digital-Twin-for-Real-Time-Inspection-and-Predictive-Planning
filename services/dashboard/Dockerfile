# ── KAVE Dashboard Service ──────────────────────────────────────────────
# Streamlit Master Dashboard (Simulation + Vision)
# استخدم نسخة حديثة ومستقرة
FROM python:3.10-slim-bookworm

WORKDIR /app

# System dependencies for PostgreSQL client
RUN sed -i 's|URIs: http://deb.debian.org/debian$|URIs: http://ftp.us.debian.org/debian|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update -o Acquire::ForceIPv4=true --fix-missing && apt-get install -o Acquire::ForceIPv4=true -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --use-deprecated=legacy-resolver -r requirements.txt

# Copy application source
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Start Streamlit
CMD ["python", "-m", "streamlit", "run", "app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true"]
