from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.db.mysql.database import Base, SessionLocal, engine, ensure_auth_schema
from app.adapters.db.mysql.models import Chapter, Experiment, Level, Question, Tool, User
from app.api.routers import auth_router, chapters_router, llm_router, tools_router, tutor_router
from app.api.routers import questions, submissions
from app.api.routers import timing_analysis
from app.api.routers import timing_challenges
from app.timing.challenge_repository import initialize_timing_challenge_pool

app = FastAPI(
    title="EDA Learning Platform",
    description="EDA learning and experiment platform backend API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chapters_router, prefix="/api/chapters", tags=["chapters"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(tools_router, prefix="/api/tools", tags=["tools"])
app.include_router(questions.router, prefix="/api", tags=["questions"])
app.include_router(submissions.router, prefix="/api", tags=["submissions"])
app.include_router(timing_analysis.router, prefix="/api/timing-analysis", tags=["timing-analysis"])
app.include_router(timing_challenges.router, prefix="/api/timing-analysis", tags=["timing-analysis"])
app.include_router(tutor_router, prefix="/api/tutor", tags=["tutor"])
app.include_router(llm_router, prefix="/v1", tags=["llm"])


@app.on_event("startup")
def init_dev_database():
    Base.metadata.create_all(bind=engine)
    ensure_auth_schema()
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.id == 1).first():
            db.add(User(id=1, username="demo"))

        chapters = [
            ("系统设计和规格定义", "明确芯片目标、系统架构、接口规格和关键约束。"),
            ("逻辑设计", "把规格转化为 RTL 模块、数据通路和控制逻辑。"),
            ("功能验证", "构建测试平台、覆盖率目标和回归验证流程。"),
            ("物理设计", "完成布局布线、时钟树、功耗和面积优化。"),
            ("时序分析和电气验证", "检查时序收敛、电压降、串扰和可靠性问题。"),
            ("DRC/LVS", "验证版图设计规则，并确认版图与原理图一致。"),
            ("制造准备与测试", "生成流片交付物，规划 DFT、ATE 和量产测试。"),
            ("芯片制造与封装", "理解晶圆制造、封装选择、良率和失效分析。"),
        ]
        level_names = [
            "概念热身",
            "流程识别",
            "关键约束",
            "工具实践",
            "问题诊断",
            "方案优化",
            "结果复盘",
            "综合挑战",
        ]

        for chapter_index, (title, description) in enumerate(chapters, start=1):
            chapter = db.query(Chapter).filter(Chapter.sort_order == chapter_index).first()
            if not chapter:
                chapter = Chapter(
                    sort_order=chapter_index,
                    title=title,
                    description=description,
                    icon="chip",
                )
                db.add(chapter)
                db.flush()

            chapter.title = title
            chapter.description = description
            chapter.icon = "chip"

            existing_levels = {
                level.sort_order: level
                for level in db.query(Level).filter(Level.chapter_id == chapter.id).all()
            }
            for level_index, level_name in enumerate(level_names, start=1):
                level = existing_levels.get(level_index)
                if not level:
                    level = Level(
                        chapter_id=chapter.id,
                        sort_order=level_index,
                        title=level_name,
                    )
                    db.add(level)
                    db.flush()

                level.title = f"{level_name}"
                level.description = f"围绕「{title}」完成第 {level_index} 个闯关任务。"
                level.question_ids = [level.id]
                level.pass_criteria = "完成本关任务并提交结果。"
                level.status = "unlocked"

                if not db.query(Question).filter(Question.level_id == level.id).first():
                    db.add(
                        Question(
                            level_id=level.id,
                            question_type="choice",
                            title=f"{title} - {level_name}",
                            content=f"本关聚焦「{title}」中的哪个学习任务？",
                            options={"A": level_name, "B": "市场推广", "C": "财务审计", "D": "人力招聘"},
                            correct_answer="A",
                            score=10,
                            difficulty=min(level_index, 5),
                            hint="题目名称就是本关重点。",
                        )
                    )

                if not db.query(Experiment).filter(Experiment.level_id == level.id).first():
                    db.add(
                        Experiment(
                            level_id=level.id,
                            name=f"{title}实验 - {level_name}",
                            goal=f"完成「{title}」阶段的{level_name}练习。",
                            input_materials="规格说明、设计文件或验证记录",
                            tools_required="EDA toolchain",
                            expected_output="形成可检查的阶段性结果。",
                            pass_criteria="结果满足本关约束并通过检查。",
                            status="pending",
                        )
                    )

        if not db.query(Tool).first():
            db.add(
                Tool(
                    name="iverilog",
                    version="dev",
                    description="Placeholder Verilog compile and simulation tool.",
                    is_active=True,
                    installed_path="local",
                )
            )

        db.commit()
    finally:
        db.close()
    initialize_timing_challenge_pool()


@app.get("/health")
def health():
    return {"status": "ok"}
