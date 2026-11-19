import os
import sys
import pytest
from sqlalchemy import event
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/psych_screening_test")

from app.core.database import Base, engine, SessionLocal, get_db
from app.core.security import hash_password
from app.models.models import Admin, AdminRole, Position, Question, AnswerOption, PositionQuestion, ResultCategory
from app.main import app
from app.core.limiter import limiter

# Rate limits are covered by a dedicated test; keep them off for everything else.
limiter.enabled = False


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        import logging
        logging.getLogger("tests").warning(f"DB setup skipped (test DB unavailable): {e}")
    yield
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception:
        pass


@pytest.fixture()
def db():
    """Each test runs inside its own outer transaction + SAVEPOINT, rolled back
    at teardown so tests never leak data into each other (proper isolation),
    even though route handlers call session.commit() internally."""
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def client(db):
    c = TestClient(app)
    c.db = db  # lets test helpers seed rows (e.g. a confirmed KTP) in the same transaction
    return c


@pytest.fixture()
def admin_token(db, client):
    admin = Admin(username="testadmin", password_hash=hash_password("TestPass123!"), role=AdminRole.superadmin)
    db.add(admin)
    db.commit()
    r = client.post("/api/admin/login", json={"username": "testadmin", "password": "TestPass123!"})
    return r.json()["access_token"]


@pytest.fixture()
def seeded_position_with_questions(db):
    position = Position(nama_jabatan="TestPosition", active=True)
    db.add(position)
    db.flush()

    questions = []
    for i in range(3):
        q = Question(question_text=f"Test question {i}", active=True)
        db.add(q)
        db.flush()
        for code, score in [("A", 0), ("B", 1), ("C", 2), ("D", 3)]:
            db.add(AnswerOption(question_id=q.id, option_code=code, option_text=code, score=score,
                                 order_number=ord(code) - ord("A")))
        db.add(PositionQuestion(position_id=position.id, question_id=q.id, order_number=i))
        questions.append(q)
    db.commit()
    return position, questions


@pytest.fixture()
def seeded_categories(db):
    cats = [
        ResultCategory(name="Low", min_score=0, max_score=3, message="low msg", recommendation="low rec"),
        ResultCategory(name="High", min_score=4, max_score=9, message="high msg", recommendation="high rec"),
    ]
    for c in cats:
        db.add(c)
    db.commit()
    return cats


def dob(age: int = 30) -> str:
    """Tanggal lahir (dd-mm-yyyy) yang menghasilkan usia `age` hari ini."""
    from datetime import timedelta
    from app.services.identity_service import today_wib
    t = today_wib()
    born = t.replace(year=t.year - age, day=min(t.day, 28)) - timedelta(days=40)
    return born.strftime("%d-%m-%Y")


def make_participant(client, jabatan="Staff", ktp_confirmed=True, **over):
    """Create a participant through the API; optionally mark the KTP as confirmed
    (screening cannot be started before that)."""
    from app.models.models import KtpDocument, Participant
    body = {"nama": "Flow Tester", "usia": 30, "jabatan": jabatan, "no_hp": "089000000000",
            "email": "flow@example.com", **over}
    r = client.post("/api/participants", json=body)
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    if ktp_confirmed:
        db = client.db
        db.add(KtpDocument(participant_id=pid, corrected_by_user=True))
        db.query(Participant).filter(Participant.id == pid).update({"nik": "3171234567890123"})
        db.commit()
    return pid
