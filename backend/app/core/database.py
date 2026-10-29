import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Serverless (Vercel): tiap invokasi singkat, jadi jangan menahan koneksi. Supabase pooler
# (pgbouncer) yang mengatur koneksi; NullPool mencegah kehabisan koneksi saat banyak instance.
_engine_kwargs = {"poolclass": NullPool} if os.getenv("VERCEL") else {"pool_pre_ping": True}
engine = create_engine(settings.DATABASE_URL, future=True, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
