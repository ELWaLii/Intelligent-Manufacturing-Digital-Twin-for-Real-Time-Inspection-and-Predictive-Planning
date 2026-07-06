# استخدم نسخة حديثة ومستقرة
FROM python:3.10-slim-bookworm

WORKDIR /app

# إضافة --fix-missing كإجراء هندسي وقائي
RUN apt-get update --fix-missing && apt-get install -y \
    libglib2.0-0 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "producer.py"]
