from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class DynamicQuestionRequest(BaseModel):
    chapter_id: int
    knowledge_point: str = None
    difficulty: int = 1

@router.post("/generate")
def generate_dynamic_question(request: DynamicQuestionRequest):
    # 当前为 Mock 数据，等大模型接口就绪后替换
    return {
        "question": {
            "title": f"动态出题 - 第{request.chapter_id}章",
            "content": f"这是关于 {request.knowledge_point or '基础概念'} 的动态题目（Mock），难度 {request.difficulty}",
            "type": "choice",
            "options": ["A. 正确", "B. 错误", "C. 不确定", "D. 需要更多信息"]
        },
        "answer": "A",
        "explanation": "这是 Mock 数据的解析，后续替换成真实大模型生成内容。"
    }