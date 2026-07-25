from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 新增导入
from app.api.routers import chapters_router, tools_router
from app.api.routers import questions
from app.api.routers import submissions

app = FastAPI(
    title="芯语智问：EDA学习平台",
    description="EDA全链路智能学习与实验平台后端接口",
    version="1.0.0"
)

# ==================== 新增 CORS 配置 ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（开发环境用，生产环境要限制）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)

# 注册路由
app.include_router(chapters_router, prefix="/api/chapters", tags=["章节管理"])
app.include_router(tools_router, prefix="/api/tools", tags=["工具管理"])
app.include_router(questions.router, prefix="/api", tags=["题目管理"])
app.include_router(submissions.router, prefix="/api", tags=["提交管理"])

@app.get("/health")
def health():
    return {"status": "ok"}