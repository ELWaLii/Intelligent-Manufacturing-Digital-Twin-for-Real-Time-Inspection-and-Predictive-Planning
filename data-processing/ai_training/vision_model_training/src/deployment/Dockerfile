# استخدام نسخة بايثون خفيفة
FROM python:3.10-slim

# تنزيل المكتبات الأساسية اللي بيحتاجها OpenCV في اللينكس
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# تحديد مسار العمل جوه الكونتينر
WORKDIR /app

# نسخ ملف المتطلبات وتنزيل المكتبات
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات المشروع (كود الـ FastAPI والأوزان)
COPY . .

# فتح بورت 8000
EXPOSE 8000

# أمر تشغيل السيرفر
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000" , "--reload"]