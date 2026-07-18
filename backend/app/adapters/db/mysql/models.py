from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    icon = Column(String(50))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    # 一对多：一个章节有多个关卡
    levels = relationship("Level", back_populates="chapter", order_by="Level.sort_order")


class Level(Base):
    __tablename__ = "levels"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(Text)
    sort_order = Column(Integer, default=0)
    question_ids = Column(JSON)  # 关联的题目ID列表
    pass_criteria = Column(Text)
    status = Column(Enum('locked', 'unlocked', 'completed'), default='locked')
    created_at = Column(DateTime, server_default=func.now())

    # 多对一：多个关卡属于一个章节
    chapter = relationship("Chapter", back_populates="levels")