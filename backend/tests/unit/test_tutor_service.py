from app.tutor.schemas import TutorAskRequest
from app.tutor.service import build_tutor_messages


def test_build_tutor_messages_keeps_question_and_context_separate():
    request = TutorAskRequest(
        question="什么是 slack？",
        context={
            "page_title": "时序分析",
            "route_path": "/chapter/5/timing-analysis",
            "selected_text": "required - arrival",
            "task_text": "计算节点 N3 的 slack",
        },
    )

    messages = build_tutor_messages(request)

    assert messages[0]["role"] == "system"
    assert "教学助教" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "学生问题：什么是 slack？" in messages[1]["content"]
    assert "页面标题: 时序分析" in messages[1]["content"]
    assert "当前任务/题目: 计算节点 N3 的 slack" in messages[1]["content"]
    assert "选中文本: required - arrival" in messages[1]["content"]

