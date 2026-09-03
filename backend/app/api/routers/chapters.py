from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.adapters.db.mysql.database import get_db
from app.adapters.db.mysql.models import Chapter, Experiment, Level

router = APIRouter()


@router.get("/")
def get_chapters(db: Session = Depends(get_db)):
    return (
        db.query(Chapter)
        .options(joinedload(Chapter.levels).joinedload(Level.experiment))
        .order_by(Chapter.sort_order)
        .all()
    )


@router.get("/levels/{level_id}")
def get_level(level_id: int, db: Session = Depends(get_db)):
    level = db.query(Level).filter(Level.id == level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    return level


@router.get("/experiments/list")
def get_experiment_levels(db: Session = Depends(get_db)):
    return db.query(Level).join(Level.experiment).filter(Experiment.id.isnot(None)).all()


@router.get("/{chapter_id}")
def get_chapter(chapter_id: int, db: Session = Depends(get_db)):
    chapter = (
        db.query(Chapter)
        .options(joinedload(Chapter.levels))
        .filter(Chapter.id == chapter_id)
        .first()
    )
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter
# ============================================================
# 关卡完成与解锁
# ============================================================

@router.post("/levels/{level_id}/complete")
def complete_level(level_id: int, db: Session = Depends(get_db)):
    # 1. 获取当前关卡
    level = db.query(Level).filter(Level.id == level_id).first()
    if not level:
        raise HTTPException(status_code=404, detail="关卡不存在")
    
    # 2. 检查是否已解锁
    if level.status == "locked":
        raise HTTPException(status_code=403, detail="关卡尚未解锁，请先完成前面的关卡")
    
    # 3. 如果已经完成，直接返回（防止重复操作）
    if level.status == "completed":
        return {
            "message": "关卡已完成",
            "level_id": level.id,
            "status": level.status,
            "next_level_id": None,
            "next_chapter_id": None
        }
    
    # 4. 标记当前关卡为 completed
    level.status = "completed"
    db.commit()
    
    # 5. 查找并解锁下一关
    next_level = db.query(Level).filter(
        Level.chapter_id == level.chapter_id,
        Level.sort_order > level.sort_order
    ).order_by(Level.sort_order).first()
    
    next_level_id = None
    next_chapter_id = None
    
    if next_level:
        next_level.status = "unlocked"
        next_level_id = next_level.id
        db.commit()
    else:
        # 当前章节最后一关完成 → 解锁下一章节
        next_chapter = db.query(Chapter).filter(
            Chapter.sort_order > level.chapter_id
        ).order_by(Chapter.sort_order).first()
        
        if next_chapter:
            next_chapter_id = next_chapter.id
            first_level = db.query(Level).filter(
                Level.chapter_id == next_chapter.id
            ).order_by(Level.sort_order).first()
            
            if first_level:
                first_level.status = "unlocked"
                next_level_id = first_level.id
                db.commit()
    
    return {
        "message": "关卡完成，已解锁下一关",
        "level_id": level.id,
        "status": level.status,
        "next_level_id": next_level_id,
        "next_chapter_id": next_chapter_id
    }