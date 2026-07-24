from fastapi import FastAPI
from app.api.routers import chapters_router, tools_router
from app.api.routers import questions  
from app.api.routers import submissions
app = FastAPI(
    title="芯语智问：EDA学习平台",
    description="EDA全链路智能学习与实验平台后端接口",
    version="1.0.0"
)

# 注册路由
app.include_router(chapters_router, prefix="/api/chapters", tags=["章节管理"])
app.include_router(tools_router, prefix="/api/tools", tags=["工具管理"])
app.include_router(questions.router, prefix="/api", tags=["题目管理"])  
app.include_router(submissions.router, prefix="/api", tags=["提交管理"])
@app.get("/health")
def health():
    return {"status": "ok"}