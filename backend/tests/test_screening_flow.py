def _create_participant(client, jabatan="TestPosition", ktp_confirmed=True):
    from tests.conftest import make_participant
    return make_participant(client, jabatan=jabatan, ktp_confirmed=ktp_confirmed)


def test_start_screening_creates_session(client, seeded_position_with_questions):
    position, _ = seeded_position_with_questions
    pid = _create_participant(client, jabatan=position.nama_jabatan)
    r = client.post("/api/screening/start", json={"participant_id": pid, "jabatan": position.nama_jabatan})
    assert r.status_code == 200
    assert "session_id" in r.json()


def test_start_screening_unknown_participant(client):
    r = client.post("/api/screening/start", json={"participant_id": "00000000-0000-0000-0000-000000000000",
                                                    "jabatan": "X"})
    assert r.status_code == 404


def test_get_questions_for_session(client, seeded_position_with_questions):
    position, questions = seeded_position_with_questions
    pid = _create_participant(client, jabatan=position.nama_jabatan)
    r = client.post("/api/screening/start", json={"participant_id": pid, "jabatan": position.nama_jabatan})
    sid = r.json()["session_id"]
    r = client.get(f"/api/screening/{sid}/questions")
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_submit_answer_and_complete_full_flow(client, seeded_position_with_questions, seeded_categories):
    position, questions = seeded_position_with_questions
    pid = _create_participant(client, jabatan=position.nama_jabatan)
    r = client.post("/api/screening/start", json={"participant_id": pid, "jabatan": position.nama_jabatan})
    sid = r.json()["session_id"]
    r = client.get(f"/api/screening/{sid}/questions")
    qs = r.json()

    for q in qs:
        opt = next(o for o in q["options"] if o["option_code"] == "B")
        r = client.post(f"/api/screening/{sid}/answers", json={"question_id": q["id"], "answer_option_id": opt["id"]})
        assert r.status_code == 200

    r = client.post(f"/api/screening/{sid}/complete")
    assert r.status_code == 200
    result = r.json()
    assert result["total_score"] == 3


def test_complete_without_all_answers_rejected(client, seeded_position_with_questions):
    position, questions = seeded_position_with_questions
    pid = _create_participant(client, jabatan=position.nama_jabatan)
    r = client.post("/api/screening/start", json={"participant_id": pid, "jabatan": position.nama_jabatan})
    sid = r.json()["session_id"]
    r = client.post(f"/api/screening/{sid}/complete")
    assert r.status_code == 400
    assert r.json()["error_code"] == "INCOMPLETE_ANSWERS"


def test_invalid_answer_option_for_question_rejected(client, seeded_position_with_questions):
    position, questions = seeded_position_with_questions
    pid = _create_participant(client, jabatan=position.nama_jabatan)
    r = client.post("/api/screening/start", json={"participant_id": pid, "jabatan": position.nama_jabatan})
    sid = r.json()["session_id"]
    r = client.get(f"/api/screening/{sid}/questions")
    qs = r.json()
    # use option from question 2 while referring to question 1 -> mismatch
    r = client.post(f"/api/screening/{sid}/answers",
                     json={"question_id": qs[0]["id"], "answer_option_id": qs[1]["options"][0]["id"]})
    assert r.status_code == 400


def test_unknown_jabatan_allows_continuing(client, seeded_position_with_questions):
    # questions exist in the system (mapped to a different, known position) but
    # none are mapped to this brand-new/unknown jabatan -> fallback must kick in
    pid = _create_participant(client, jabatan="Jabatan Sangat Unik Belum Terdaftar")
    r = client.post("/api/screening/start",
                     json={"participant_id": pid, "jabatan": "Jabatan Sangat Unik Belum Terdaftar"})
    assert r.status_code == 200
    sid = r.json()["session_id"]
    r = client.get(f"/api/screening/{sid}/questions")
    assert r.status_code == 200  # must not error even with no dedicated mapping
    assert len(r.json()) > 0  # must fall back to a general question set, never leave the user stuck


def test_start_screening_requires_confirmed_ktp(client, seeded_position_with_questions):
    position, _ = seeded_position_with_questions
    pid = _create_participant(client, jabatan=position.nama_jabatan, ktp_confirmed=False)
    r = client.post("/api/screening/start", json={"participant_id": pid, "jabatan": position.nama_jabatan})
    assert r.status_code == 403
    assert r.json()["error_code"] == "KTP_NOT_CONFIRMED"


def test_rescanning_ktp_requires_confirming_again(client, seeded_position_with_questions):
    from app.models.models import KtpDocument
    position, _ = seeded_position_with_questions
    pid = _create_participant(client, jabatan=position.nama_jabatan)
    assert client.get(f"/api/participants/{pid}").json()["ktp_confirmed"] is True
    # a fresh upload replaces the document with an unconfirmed one
    client.db.query(KtpDocument).filter(KtpDocument.participant_id == pid).delete()
    client.db.add(KtpDocument(participant_id=pid))
    client.db.commit()
    assert client.get(f"/api/participants/{pid}").json()["ktp_confirmed"] is False
    r = client.post("/api/screening/start", json={"participant_id": pid, "jabatan": position.nama_jabatan})
    assert r.status_code == 403


def _complete_screening(client, position):
    """Register a participant, confirm KTP, answer everything, and complete the session."""
    pid = _create_participant(client, jabatan=position.nama_jabatan)
    sid = client.post("/api/screening/start", json={"participant_id": pid, "jabatan": position.nama_jabatan}).json()["session_id"]
    qs = client.get(f"/api/screening/{sid}/questions").json()
    for q in qs:
        opt = next(o for o in q["options"] if o["option_code"] == "B")
        client.post(f"/api/screening/{sid}/answers", json={"question_id": q["id"], "answer_option_id": opt["id"]})
    r = client.post(f"/api/screening/{sid}/complete")
    assert r.status_code == 200, r.text
    return pid, sid


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- retake requests ----------
def test_cannot_restart_after_completion_without_approval(client, seeded_position_with_questions, seeded_categories):
    position, _ = seeded_position_with_questions
    pid, _ = _complete_screening(client, position)
    r = client.post("/api/screening/start", json={"participant_id": pid, "jabatan": position.nama_jabatan})
    assert r.status_code == 403 and r.json()["error_code"] == "RETAKE_NOT_APPROVED"


def test_cannot_request_retake_without_completed_session(client, seeded_position_with_questions):
    position, _ = seeded_position_with_questions
    pid = _create_participant(client, jabatan=position.nama_jabatan)
    r = client.post(f"/api/participants/{pid}/retake-requests", json={})
    assert r.status_code == 400 and r.json()["error_code"] == "NO_COMPLETED_SCREENING"


def test_retake_request_full_cycle(client, admin_token, seeded_position_with_questions, seeded_categories):
    position, _ = seeded_position_with_questions
    pid, _ = _complete_screening(client, position)

    # 1. request retake
    r = client.post(f"/api/participants/{pid}/retake-requests", json={"reason": "Ingin mengulang"})
    assert r.status_code == 201 and r.json()["status"] == "pending"
    profile = client.get(f"/api/participants/{pid}").json()
    assert profile["retake_status"] == "pending"

    # 2. duplicate request while pending is rejected
    r = client.post(f"/api/participants/{pid}/retake-requests", json={})
    assert r.status_code == 409 and r.json()["error_code"] == "RETAKE_REQUEST_EXISTS"

    # 3. still blocked from starting until approved
    r = client.post("/api/screening/start", json={"participant_id": pid, "jabatan": position.nama_jabatan})
    assert r.status_code == 403

    # 4. admin sees it pending and approves
    pending = client.get("/api/admin/retake-requests?status=pending", headers=_auth(admin_token)).json()
    assert pending["total"] == 1
    req_id = pending["items"][0]["id"]
    assert pending["items"][0]["participant_nama"]
    assert client.get("/api/admin/retake-requests/pending-count", headers=_auth(admin_token)).json()["pending"] == 1

    r = client.post(f"/api/admin/retake-requests/{req_id}/decision", json={"status": "approved"}, headers=_auth(admin_token))
    assert r.status_code == 200 and r.json()["status"] == "approved"

    profile = client.get(f"/api/participants/{pid}").json()
    assert profile["retake_status"] == "approved"

    # 5. deciding again is rejected
    r = client.post(f"/api/admin/retake-requests/{req_id}/decision", json={"status": "rejected"}, headers=_auth(admin_token))
    assert r.status_code == 409 and r.json()["error_code"] == "RETAKE_ALREADY_DECIDED"

    # 6. now starting works, and the approval is consumed (one-time use)
    r = client.post("/api/screening/start", json={"participant_id": pid, "jabatan": position.nama_jabatan})
    assert r.status_code == 200
    profile = client.get(f"/api/participants/{pid}").json()
    assert profile["retake_status"] is None
    assert profile["in_progress_session_id"] is not None

    # 7. a further retake needs a brand new approval
    r = client.post("/api/screening/start", json={"participant_id": pid, "jabatan": position.nama_jabatan})
    assert r.status_code == 200 and r.json()["resumed"] is True  # same in-progress session resumes


def test_retake_request_rejected_can_be_resubmitted(client, admin_token, seeded_position_with_questions, seeded_categories):
    position, _ = seeded_position_with_questions
    pid, _ = _complete_screening(client, position)
    client.post(f"/api/participants/{pid}/retake-requests", json={})
    req_id = client.get("/api/admin/retake-requests?status=pending", headers=_auth(admin_token)).json()["items"][0]["id"]

    r = client.post(f"/api/admin/retake-requests/{req_id}/decision",
                     json={"status": "rejected", "admin_note": "Belum waktunya"}, headers=_auth(admin_token))
    assert r.status_code == 200 and r.json()["admin_note"] == "Belum waktunya"

    profile = client.get(f"/api/participants/{pid}").json()
    assert profile["retake_status"] == "rejected"

    r = client.post("/api/screening/start", json={"participant_id": pid, "jabatan": position.nama_jabatan})
    assert r.status_code == 403

    # rejected doesn't block filing a new request
    r = client.post(f"/api/participants/{pid}/retake-requests", json={})
    assert r.status_code == 201


def test_retake_endpoints_require_admin_auth(client, seeded_position_with_questions, seeded_categories):
    position, _ = seeded_position_with_questions
    pid, _ = _complete_screening(client, position)
    client.post(f"/api/participants/{pid}/retake-requests", json={})
    assert client.get("/api/admin/retake-requests").status_code == 401
    assert client.get("/api/admin/retake-requests/pending-count").status_code == 401
    assert client.post("/api/admin/retake-requests/x/decision", json={"status": "approved"}).status_code == 401
