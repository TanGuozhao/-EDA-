from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, JSON, ForeignKey, Boolean
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
    # 一对多：一个关卡有多个题目
    questions = relationship("Question", back_populates="level")
    # 一对一：一个关卡有一个实验（可选）
    experiment = relationship("Experiment", back_populates="level", uselist=False)


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    level_id = Column(Integer, ForeignKey("levels.id"), nullable=False)
    question_type = Column(Enum('choice', 'qa', 'code', 'experiment'), default='choice')
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)  # 题干
    options = Column(JSON)  # 选择题选项 {"A": "...", "B": "..."}
    correct_answer = Column(Text, nullable=False)  # 标准答案
    score = Column(Integer, default=10)
    difficulty = Column(Integer, default=1)  # 1-5
    hint = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    # 多对一：多个题目属于一个关卡
    level = relationship("Level", back_populates="questions")


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, index=True)
    level_id = Column(Integer, ForeignKey("levels.id"), nullable=False)
    name = Column(String(100), nullable=False)
    goal = Column(Text)
    input_materials = Column(Text)
    tools_required = Column(String(255))
    expected_output = Column(Text)
    pass_criteria = Column(Text)
    status = Column(Enum('pending', 'running', 'passed', 'failed'), default='pending')
    created_at = Column(DateTime, server_default=func.now())

    # 多对一：多个实验属于一个关卡（但这里设计为一对一）
    level = relationship("Level", back_populates="experiment")


class Tool(Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    version = Column(String(20))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    installed_path = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"))
    experiment_id = Column(Integer, ForeignKey("experiments.id"))
    submission_type = Column(Enum('question', 'experiment'), nullable=False)
    user_answer = Column(Text)
    result = Column(Text)
    score = Column(Integer, default=0)
    status = Column(Enum('pending', 'correct', 'wrong', 'error'), default='pending')
    tool_output = Column(Text)
    submitted_at = Column(DateTime, server_default=func.now())