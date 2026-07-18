from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.adapters.db.mysql.database import get_db
from app.adapters.db.mysql.models import Chapter

router = APIRouter()

@router.get("/")
def get_chapters(db: Session = Depends(get_db)):
    chapters = db.query(Chapter).order_by(Chapter.sort_order).all()
    return chapters
@router.get("/{chapter_id}")
def get_chapter(chapter_id: int, db: Session = Depends(get_db)):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    return chapter