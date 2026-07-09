# ── KAVE Vision Engine Service ──────────────────────────────────────────
# FastAPI + Redis Consumer for PatchCore Anomaly Detection
# استخدم نسخة حديثة ومستقرة
FROM python:3.10-slim-bookworm

WORKDIR /app

# إضافة --fix-missing كإجراء هندسي وقائي
RUN sed -i 's/deb.debian.org/ftp.us.debian.org/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update -o Acquire::ForceIPv4=true --fix-missing && apt-get install -o Acquire::ForceIPv4=true -y \
    libglib2.0-0 \
    libgl1-mesa-glx \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (heavy AI libs cached in this layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source, config, and model weights
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Health check for container orchestration


# Start FastAPI (no --reload in production)
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

