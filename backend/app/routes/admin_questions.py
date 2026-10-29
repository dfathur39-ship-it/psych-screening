from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_admin
from app.core.errors import not_found
from app.models.models import Question, AnswerOption, PositionQuestion, Admin
from app.schemas.schemas import QuestionCreate, QuestionUpdate, QuestionOut, PaginatedResponse
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/admin/questions", tags=["admin-questions"])


def _to_out(q: Question) -> QuestionOut:
    return QuestionOut(
        id=q.id,
        question_text=q.question_text,
        active=q.active,
        options=[o for o in q.answer_options],
        position_ids=[pl.position_id for pl in q.position_links],
        created_at=q.created_at,
    )


@router.get("", response_model=PaginatedResponse)
def list_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    active: bool | None = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    query = db.query(Question).options(
        joinedload(Question.answer_options), joinedload(Question.position_links)
    )
    if active is not None:
        query = query.filter(Question.active == active)
    total = query.count()
    items = (
        query.order_by(Question.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedResponse(
        items=[_to_out(q) for q in items],
        total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=QuestionOut, status_code=201)
def create_question(payload: QuestionCreate, request: Request, db: Session = Depends(get_db),
                     admin: Admin = Depends(get_current_admin)):
    question = Question(question_text=payload.question_text.strip(), active=payload.active)
    db.add(question)
    db.flush()

    for opt in payload.options:
        db.add(AnswerOption(
            question_id=question.id, option_code=opt.option_code,
            option_text=opt.option_text, score=opt.score, order_number=opt.order_number,
        ))

    for idx, pos_id in enumerate(payload.position_ids):
        db.add(PositionQuestion(position_id=pos_id, question_id=question.id, order_number=idx))

    db.commit()
    db.refresh(question)
    log_action(db, admin.id, "CREATE_QUESTION", "question", question.id,
               f"Membuat pertanyaan baru", request.client.host if request.client else None)
    return _to_out(question)


@router.get("/{question_id}", response_model=QuestionOut)
def get_question(question_id: str, db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise not_found("Pertanyaan tidak ditemukan", "QUESTION_NOT_FOUND")
    return _to_out(question)


@router.put("/{question_id}", response_model=QuestionOut)
def update_question(question_id: str, payload: QuestionUpdate, request: Request,
                     db: Session = Depends(get_db), admin: Admin = Depends(get_current_admin)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise not_found("Pertanyaan tidak ditemukan", "QUESTION_NOT_FOUND")

    if payload.question_text is not None:
        question.question_text = payload.question_text.strip()
    if payload.active is not None:
        question.active = payload.active

    if payload.options is not None:
        db.query(AnswerOption).filter(AnswerOption.question_id == question.id).delete()
        db.flush()
        for opt in payload.options:
            db.add(AnswerOption(
                question_id=question.id, option_code=opt.option_code,
                option_text=opt.option_text, score=opt.score, order_number=opt.order_number,
            ))

    if payload.position_ids is not None:
        db.query(PositionQuestion).filter(PositionQuestion.question_id == question.id).delete()
        db.flush()
        for idx, pos_id in enumerate(payload.position_ids):
            db.add(PositionQuestion(position_id=pos_id, question_id=question.id, order_number=idx))

    db.commit()
    db.refresh(question)
    log_action(db, admin.id, "UPDATE_QUESTION", "question", question.id,
               "Mengubah pertanyaan", request.client.host if request.client else None)
    return _to_out(question)


@router.delete("/{question_id}")
def delete_question(question_id: str, request: Request, db: Session = Depends(get_db),
                     admin: Admin = Depends(get_current_admin)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise not_found("Pertanyaan tidak ditemukan", "QUESTION_NOT_FOUND")
    db.delete(question)
    db.commit()
    log_action(db, admin.id, "DELETE_QUESTION", "question", question_id,
               "Menghapus pertanyaan", request.client.host if request.client else None)
    return {"success": True, "message": "Pertanyaan dihapus"}
