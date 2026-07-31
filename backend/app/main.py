import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ========== 远程版本的路由 ==========
from app.api.routers.auth import router as auth_router
from app.api.routers.chapters import router as chapters_router
from app.api.routers.chat import router as chat_router
from app.api.routers.hls_challenges import router as hls_challenges_router
from app.api.routers.llm import router as llm_router
from app.api.routers.tools import router as tools_router
from app.api.routers.tutor import router as tutor_router
from app.api.routers.yosys_design import router as yosys_design_router
from app.api.routers.yosys_verilog import router as yosys_verilog_router
from app.api.routers import questions, submissions, timing_analysis, timing_challenges

# ========== 你本地版本的路由 ==========
from app.api.routers import profile
from app.api.routers import dynamic_questions
from app.api.routers import rtl, hls  # 新加的任务一和任务二

app = FastAPI(
    title="EDA Learning Platform",
    description="EDA learning and experiment platform backend API",
    version="1.0.0",
)


def get_cors_origins() -> list[str]:
    configured_origins = os.getenv("CORS_ALLOW_ORIGINS", "")
    return [origin.strip() for origin in configured_origins.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 注册路由 ==========

# 远程版本的路由
app.include_router(chapters_router, prefix="/api/chapters", tags=["chapters"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(tools_router, prefix="/api/tools", tags=["tools"])
app.include_router(yosys_verilog_router, prefix="/api/tools/yosys/verilog", tags=["yosys-verilog"])
app.include_router(yosys_design_router, prefix="/api/tools/yosys/design", tags=["yosys-design"])
app.include_router(questions.router, prefix="/api", tags=["questions"])
app.include_router(submissions.router, prefix="/api", tags=["submissions"])
app.include_router(timing_analysis.router, prefix="/api/timing-analysis", tags=["timing-analysis"])
app.include_router(timing_challenges.router, prefix="/api/timing-analysis", tags=["timing-analysis"])
app.include_router(hls_challenges_router, prefix="/api/hls", tags=["hls"])
app.include_router(tutor_router, prefix="/api/tutor", tags=["tutor"])
app.include_router(llm_router, prefix="/v1", tags=["llm"])

# 你本地版本的路由（保留）
app.include_router(profile.router, prefix="/api/profile", tags=["学习画像"])
app.include_router(dynamic_questions.router, prefix="/api/dynamic", tags=["动态出题"])

# 新加的任务一和任务二
app.include_router(rtl.router, prefix="/api/rtl", tags=["RTL设计"])
app.include_router(hls.router, prefix="/api/hls", tags=["高级综合"])


@app.get("/health")
def health():
    return {"status": "ok"}