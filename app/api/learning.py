from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import get_demo_or_current_user
from app.core.database import get_db
from app.models.user import CodeExecutionRecord, Level, StudyRecord, User, UserProgress
from app.services.learning import build_progress_summary, calculate_level_status


router = APIRouter()


class ApiResponse(BaseModel):
    code: int = 200
    msg: str = "操作成功"
    data: dict


class LevelCreate(BaseModel):
    level_name: str
    title: str
    description: str
    initial_code: str
    expected_output: str
    steps: str
    hint: Optional[str] = None
    theme: Optional[str] = None
    sort_order: int = 0


class StudyRecordIn(BaseModel):
    study_date: date = Field(..., description="YYYY-MM-DD")
    content: str
    duration: int = 0
    mood: str = "一般"


class ProgressCompleteIn(BaseModel):
    level_id: int
    score: int = 100


def get_highest_completed_level(db: Session, user_id: int) -> int:
    value = (
        db.query(func.max(UserProgress.level_id))
        .filter(UserProgress.user_id == user_id, UserProgress.status == "completed")
        .scalar()
    )
    return int(value or 0)


def serialize_level(level: Level, status: str) -> dict:
    return {
        "id": level.id,
        "level_name": level.level_name,
        "name": level.level_name,
        "title": level.title,
        "description": level.description,
        "initial_code": level.initial_code,
        "expected_output": level.expected_output,
        "steps": level.steps.splitlines(),
        "hint": level.hint,
        "theme": level.theme,
        "sort_order": level.sort_order,
        "status": status,
        "badge": "已点亮" if status == "completed" else "挑战中" if status == "current" else "待点亮",
    }


def upsert_completed_progress(db: Session, user_id: int, level_id: int, score: int = 100):
    progress = (
        db.query(UserProgress)
        .filter(UserProgress.user_id == user_id, UserProgress.level_id == level_id)
        .first()
    )
    if progress:
        progress.status = "completed"
        progress.score = max(progress.score or 0, score)
        progress.completed_at = progress.completed_at or datetime.now()
    else:
        progress = UserProgress(
            user_id=user_id,
            level_id=level_id,
            status="completed",
            score=score,
            completed_at=datetime.now(),
        )
        db.add(progress)
    return progress


def month_range(month: str):
    start = datetime.strptime(month, "%Y-%m").date()
    if start.month == 12:
        end = date(start.year + 1, 1, 1)
    else:
        end = date(start.year, start.month + 1, 1)
    return start, end


@router.get("/levels")
async def list_levels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_demo_or_current_user),
):
    levels = db.query(Level).filter(Level.status == "enabled").order_by(Level.sort_order.asc(), Level.id.asc()).all()
    highest_completed = get_highest_completed_level(db, current_user.id)
    data = [
        serialize_level(level, calculate_level_status(level.id, highest_completed))
        for level in levels
    ]
    return ApiResponse(
        msg="获取成功",
        data={
            "levels": data,
            "summary": build_progress_summary(highest_completed, len(levels)),
        },
    )


@router.get("/levels/{level_id}")
async def get_level(
    level_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_demo_or_current_user),
):
    level = db.query(Level).filter(Level.id == level_id, Level.status == "enabled").first()
    if not level:
        return ApiResponse(code=404, msg="关卡不存在", data={})
    highest_completed = get_highest_completed_level(db, current_user.id)
    return ApiResponse(
        msg="获取成功",
        data={"level": serialize_level(level, calculate_level_status(level.id, highest_completed))},
    )


@router.post("/levels")
async def create_level(payload: LevelCreate, db: Session = Depends(get_db)):
    level = Level(**payload.dict(), status="enabled")
    db.add(level)
    db.commit()
    db.refresh(level)
    return ApiResponse(code=201, msg="创建成功", data={"id": level.id})


@router.put("/levels/{level_id}")
async def update_level(level_id: int, payload: LevelCreate, db: Session = Depends(get_db)):
    level = db.query(Level).filter(Level.id == level_id).first()
    if not level:
        return ApiResponse(code=404, msg="关卡不存在", data={})
    for key, value in payload.dict().items():
        setattr(level, key, value)
    db.commit()
    return ApiResponse(msg="更新成功", data={"id": level.id})


@router.delete("/levels/{level_id}")
async def delete_level(level_id: int, db: Session = Depends(get_db)):
    level = db.query(Level).filter(Level.id == level_id).first()
    if not level:
        return ApiResponse(code=404, msg="关卡不存在", data={})
    level.status = "disabled"
    db.commit()
    return ApiResponse(msg="删除成功", data={})


@router.get("/progress")
async def get_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_demo_or_current_user),
):
    progress_rows = db.query(UserProgress).filter(UserProgress.user_id == current_user.id).all()
    highest_completed = get_highest_completed_level(db, current_user.id)
    total_levels = db.query(Level).filter(Level.status == "enabled").count()
    return ApiResponse(
        msg="获取成功",
        data={
            "highest_completed": highest_completed,
            "summary": build_progress_summary(highest_completed, total_levels),
            "progress": [
                {
                    "level_id": row.level_id,
                    "status": row.status,
                    "score": row.score,
                    "completed_at": row.completed_at,
                }
                for row in progress_rows
            ],
        },
    )


@router.post("/progress/complete")
async def complete_progress(
    payload: ProgressCompleteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_demo_or_current_user),
):
    level = db.query(Level).filter(Level.id == payload.level_id, Level.status == "enabled").first()
    if not level:
        return ApiResponse(code=404, msg="关卡不存在", data={})
    upsert_completed_progress(db, current_user.id, payload.level_id, payload.score)
    db.commit()
    return ApiResponse(msg="通关进度已保存", data={"level_id": payload.level_id})


@router.get("/study-records")
async def list_study_records(
    month: Optional[str] = Query(None, description="YYYY-MM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_demo_or_current_user),
):
    query = db.query(StudyRecord).filter(StudyRecord.user_id == current_user.id)
    if month:
        start, end = month_range(month)
        query = query.filter(StudyRecord.study_date >= start, StudyRecord.study_date < end)
    records = query.order_by(StudyRecord.study_date.desc()).all()
    return ApiResponse(
        msg="获取成功",
        data={
            "records": [
                {
                    "date": row.study_date.isoformat(),
                    "content": row.content,
                    "duration": row.duration,
                    "mood": row.mood,
                    "updatedAt": row.updated_at,
                }
                for row in records
            ]
        },
    )


@router.post("/study-records")
async def save_study_record(
    payload: StudyRecordIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_demo_or_current_user),
):
    record = (
        db.query(StudyRecord)
        .filter(StudyRecord.user_id == current_user.id, StudyRecord.study_date == payload.study_date)
        .first()
    )
    if record:
        record.content = payload.content
        record.duration = max(0, payload.duration)
        record.mood = payload.mood
    else:
        record = StudyRecord(
            user_id=current_user.id,
            study_date=payload.study_date,
            content=payload.content,
            duration=max(0, payload.duration),
            mood=payload.mood,
        )
        db.add(record)
    db.commit()
    return ApiResponse(msg="保存成功", data={"date": payload.study_date.isoformat()})


@router.delete("/study-records/{study_date}")
async def delete_study_record(
    study_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_demo_or_current_user),
):
    record = (
        db.query(StudyRecord)
        .filter(StudyRecord.user_id == current_user.id, StudyRecord.study_date == study_date)
        .first()
    )
    if not record:
        return ApiResponse(code=404, msg="打卡记录不存在", data={})
    db.delete(record)
    db.commit()
    return ApiResponse(msg="删除成功", data={})


@router.get("/study-statistics")
async def get_study_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_demo_or_current_user),
):
    total_levels = db.query(Level).filter(Level.status == "enabled").count()
    highest_completed = get_highest_completed_level(db, current_user.id)
    study_days = db.query(StudyRecord).filter(StudyRecord.user_id == current_user.id).count()
    code_runs = db.query(CodeExecutionRecord).filter(CodeExecutionRecord.user_id == current_user.id).count()
    passed_runs = (
        db.query(CodeExecutionRecord)
        .filter(CodeExecutionRecord.user_id == current_user.id, CodeExecutionRecord.passed == True)
        .count()
    )
    return ApiResponse(
        msg="获取成功",
        data={
            "summary": build_progress_summary(highest_completed, total_levels),
            "study_days": study_days,
            "code_runs": code_runs,
            "passed_runs": passed_runs,
        },
    )
