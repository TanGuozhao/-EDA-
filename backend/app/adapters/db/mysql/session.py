# name=backend/app/adapters/db/mysql/session.py
"""
数据库连接与 Session 管理（同步 SQLAlchemy 简易封装）
生产环境请使用连接池和更完善的配置管理
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv
load_dotenv()
# 从环境变量读取数据库 URL，提供默认占位符
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://user:password@127.0.0.1:3306/eda_db?charset=utf8mb4")

# 同步 engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

# Session 工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基类
Base = declarative_base()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()