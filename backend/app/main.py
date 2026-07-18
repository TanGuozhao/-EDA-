from fastapi import FastAPI
from app.api.routers import chapters

app = FastAPI(title="芯语智问：EDA学习平台")

app.include_router(chapters.router, prefix="/api/chapters", tags=["chapters"])

@app.get("/health")
def health():
    return {"status": "ok"}