from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings

# إنشاء محرك الاتصال
engine = create_engine(settings.DATABASE_URL)

# تكوين الجلسات المحلية
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# دالة الـ Dependency لحقن الجلسة في الـ Endpoints وقفلها أوتوماتيكياً
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()