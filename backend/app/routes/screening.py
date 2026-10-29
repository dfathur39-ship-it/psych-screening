from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import not_found, bad_request, conflict, forbidden
from app.models.models import (
    Participant, ScreeningSession, ScreeningAnswer, AnswerOption, Question,
    PositionQuestion, SessionStatus,
)
from app.schemas.schemas import (
    ScreeningStart, ScreeningAnswerSubmit, ScreeningResultOut, QuestionPublicOut, AnswerOptionOutPublic,
)
from app.services.participant_service import get_unused_approved_retake, has_completed_session, is_ktp_confirmed
from app.services.position_resolver import resolve_position, get_questions_for_position
from app.services.scoring.engine import ScoringEngine

router = APIRouter(prefix="/api/screening", tags=["screening"])


@router.post("/start")
def start_screening(payload: ScreeningStart, db: Session = Depends(get_db)):
    participant = db.query(Participant).filter(Participant.id == payload.participant_id).first()
    if not participant:
        raise not_found("Peserta tidak ditemukan", "PARTICIPANT_NOT_FOUND")

    # Pertanyaan baru hanya bisa dimulai setelah KTP dikonfirmasi di profil.
    if not is_ktp_confirmed(participant):
        raise forbidden("Konfirmasi KTP di halaman profil sebelum memulai skrining", "KTP_NOT_CONFIRMED")

    existing = (
        db.query(ScreeningSession)
        .filter(ScreeningSession.participant_id == participant.id,
                ScreeningSession.status == SessionStatus.in_progress)
        .first()
    )
    if existing:
        return {"session_id": existing.id, "resumed": True}

    # Sudah pernah menyelesaikan skrining: perlu izin admin (permintaan mengerjakan ulang yang disetujui)
    # sebelum bisa mulai lagi. Izin itu berlaku sekali pakai.
    if has_completed_session(db, participant.id):
        approved = get_unused_approved_retake(db, participant.id)
        if not approved:
            raise forbidden(
                "Skrining Anda sudah selesai. Ajukan permintaan mengerjakan ulang di beranda dan tunggu "
                "persetujuan admin.",
                "RETAKE_NOT_APPROVED",
            )
        approved.status = "used"

    position = resolve_position(db, payload.jabatan)

    session = ScreeningSession(participant_id=participant.id, position_id=position.id,
                                status=SessionStatus.in_progress)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "resumed": False}


@router.get("/{session_id}/questions", response_model=list[QuestionPublicOut])
def get_session_questions(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ScreeningSession).filter(ScreeningSession.id == session_id).first()
    if not session:
        raise not_found("Sesi skrining tidak ditemukan", "SESSION_NOT_FOUND")

    questions = get_questions_for_position(db, session.position)
    answered_map = {a.question_id: a.answer_option_id for a in session.answers}

    result = []
    for idx, q in enumerate(questions):
        order = next(
            (pq.order_number for pq in q.position_links if pq.position_id == session.position_id),
            idx,
        )
        result.append(QuestionPublicOut(
            id=q.id,
            question_text=q.question_text,
            order_number=order,
            options=[AnswerOptionOutPublic.model_validate(o) for o in q.answer_options],
            answered_option_id=answered_map.get(q.id),
        ))
    result.sort(key=lambda q: q.order_number)
    return result


@router.post("/{session_id}/answers")
def submit_answer(session_id: str, payload: ScreeningAnswerSubmit, db: Session = Depends(get_db)):
    session = db.query(ScreeningSession).filter(ScreeningSession.id == session_id).first()
    if not session:
        raise not_found("Sesi skrining tidak ditemukan", "SESSION_NOT_FOUND")
    if session.status != SessionStatus.in_progress:
        raise conflict("Sesi skrining sudah selesai, tidak dapat mengubah jawaban", "SESSION_ALREADY_COMPLETED")

    question = db.query(Question).filter(Question.id == payload.question_id).first()
    if not question:
        raise not_found("Pertanyaan tidak ditemukan", "QUESTION_NOT_FOUND")

    allowed_questions = get_questions_for_position(db, session.position)
    if payload.question_id not in {q.id for q in allowed_questions}:
        raise bad_request("Pertanyaan ini bukan bagian dari sesi skrining Anda", "QUESTION_NOT_IN_SESSION")

    option = db.query(AnswerOption).filter(
        AnswerOption.id == payload.answer_option_id,
        AnswerOption.question_id == payload.question_id,
    ).first()
    if not option:
        raise bad_request("Opsi jawaban tidak valid untuk pertanyaan ini", "INVALID_ANSWER_OPTION")

    existing_answer = db.query(ScreeningAnswer).filter(
        ScreeningAnswer.screening_session_id == session_id,
        ScreeningAnswer.question_id == payload.question_id,
    ).first()

    if existing_answer:
        existing_answer.answer_option_id = option.id
        existing_answer.score = option.score
    else:
        existing_answer = ScreeningAnswer(
            screening_session_id=session_id,
            question_id=question.id,
            answer_option_id=option.id,
            score=option.score,
        )
        db.add(existing_answer)

    db.commit()
    return {"success": True, "message": "Jawaban tersimpan"}


@router.post("/{session_id}/complete", response_model=ScreeningResultOut)
def complete_screening(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ScreeningSession).filter(ScreeningSession.id == session_id).first()
    if not session:
        raise not_found("Sesi skrining tidak ditemukan", "SESSION_NOT_FOUND")
    if session.status == SessionStatus.completed:
        return _build_result(db, session)

    expected_questions = get_questions_for_position(db, session.position)
    answered_ids = {a.question_id for a in session.answers}
    missing = [q for q in expected_questions if q.id not in answered_ids]
    if missing:
        raise bad_request(
            f"Masih ada {len(missing)} pertanyaan yang belum dijawab",
            "INCOMPLETE_ANSWERS",
        )

    engine = ScoringEngine(db)
    session = engine.finalize_session(session)
    return _build_result(db, session)


@router.get("/{session_id}/result", response_model=ScreeningResultOut)
def get_result(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ScreeningSession).filter(ScreeningSession.id == session_id).first()
    if not session:
        raise not_found("Sesi skrining tidak ditemukan", "SESSION_NOT_FOUND")
    if session.status != SessionStatus.completed:
        raise bad_request("Sesi skrining belum selesai", "SESSION_NOT_COMPLETED")
    return _build_result(db, session)


def _build_result(db: Session, session: ScreeningSession) -> ScreeningResultOut:
    category = session.result_category
    return ScreeningResultOut(
        session_id=session.id,
        total_score=session.total_score or 0,
        category_name=category.name if category else "Tidak terklasifikasi",
        message=category.message if category else (
            "Skor Anda saat ini belum memiliki kategori yang sesuai di sistem. "
            "Silakan hubungi admin/psikolog untuk peninjauan lebih lanjut."
        ),
        recommendation=category.recommendation if category else "Hubungi tim HR/psikolog untuk tindak lanjut.",
    )
