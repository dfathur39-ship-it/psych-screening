from app.services.scoring.engine import ScoringEngine
from app.models.models import ScreeningSession, ScreeningAnswer, Participant, SessionStatus


def _make_session(db, position, participant_nama="Tester"):
    participant = Participant(nama=participant_nama, usia=25, jabatan="Y", no_hp="080000000000")
    db.add(participant)
    db.flush()
    session = ScreeningSession(participant_id=participant.id, position_id=position.id,
                                status=SessionStatus.in_progress)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def test_scoring_all_a(db, seeded_position_with_questions, seeded_categories):
    position, questions = seeded_position_with_questions
    session = _make_session(db, position)
    for q in questions:
        opt_a = next(o for o in q.answer_options if o.option_code == "A")
        db.add(ScreeningAnswer(screening_session_id=session.id, question_id=q.id,
                                answer_option_id=opt_a.id, score=opt_a.score))
    db.commit()

    engine = ScoringEngine(db)
    total = engine.compute_total_score(session.id)
    assert total == 0  # A+A+A = 0+0+0


def test_scoring_mixed_answers(db, seeded_position_with_questions, seeded_categories):
    position, questions = seeded_position_with_questions
    session = _make_session(db, position)
    codes = ["A", "B", "C"]  # only 3 questions in fixture
    for q, code in zip(questions, codes):
        opt = next(o for o in q.answer_options if o.option_code == code)
        db.add(ScreeningAnswer(screening_session_id=session.id, question_id=q.id,
                                answer_option_id=opt.id, score=opt.score))
    db.commit()

    engine = ScoringEngine(db)
    total = engine.compute_total_score(session.id)
    # A=0, B=1, C=2 -> total 3
    assert total == 3


def test_resolve_category_boundary_min(db, seeded_position_with_questions, seeded_categories):
    engine = ScoringEngine(db)
    category = engine.resolve_category(0)
    assert category.name == "Low"


def test_resolve_category_boundary_max(db, seeded_position_with_questions, seeded_categories):
    engine = ScoringEngine(db)
    category = engine.resolve_category(3)
    assert category.name == "Low"
    category = engine.resolve_category(4)
    assert category.name == "High"


def test_resolve_category_no_match_returns_none(db, seeded_position_with_questions, seeded_categories):
    engine = ScoringEngine(db)
    category = engine.resolve_category(100)  # above all ranges
    assert category is None


def test_resolve_category_inactive_excluded(db, seeded_position_with_questions):
    from app.models.models import ResultCategory
    cat = ResultCategory(name="Inactive", min_score=0, max_score=10, message="m", recommendation="r", active=False)
    db.add(cat)
    db.commit()

    engine = ScoringEngine(db)
    category = engine.resolve_category(5)
    assert category is None  # inactive category must not match


def test_resolve_category_overlap_picks_narrowest(db, seeded_position_with_questions):
    from app.models.models import ResultCategory
    wide = ResultCategory(name="Wide", min_score=0, max_score=20, message="m", recommendation="r", active=True)
    narrow = ResultCategory(name="Narrow", min_score=5, max_score=8, message="m", recommendation="r", active=True)
    db.add_all([wide, narrow])
    db.commit()

    engine = ScoringEngine(db)
    category = engine.resolve_category(6)
    assert category.name == "Narrow"


def test_finalize_session_sets_status_completed(db, seeded_position_with_questions, seeded_categories):
    position, questions = seeded_position_with_questions
    session = _make_session(db, position)
    for q in questions:
        opt_b = next(o for o in q.answer_options if o.option_code == "B")
        db.add(ScreeningAnswer(screening_session_id=session.id, question_id=q.id,
                                answer_option_id=opt_b.id, score=opt_b.score))
    db.commit()

    engine = ScoringEngine(db)
    finalized = engine.finalize_session(session)
    assert finalized.status == SessionStatus.completed
    assert finalized.total_score == 3  # B+B+B = 1+1+1
    assert finalized.result_category_id is not None
    assert finalized.completed_at is not None
