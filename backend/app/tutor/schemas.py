from pydantic import BaseModel, Field


class TutorContext(BaseModel):
    page_title: str | None = Field(default=None, max_length=200)
    route_path: str | None = Field(default=None, max_length=300)
    selected_text: str | None = Field(default=None, max_length=2000)
    page_text: str | None = Field(default=None, max_length=4000)
    learning_stage: str | None = Field(default=None, max_length=200)
    task_text: str | None = Field(default=None, max_length=2000)


class TutorAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    context: TutorContext = Field(default_factory=TutorContext)
    max_tokens: int = Field(default=700, ge=64, le=2000)
    temperature: float = Field(default=0.2, ge=0, le=1)


class TutorAskResponse(BaseModel):
    reply: str

