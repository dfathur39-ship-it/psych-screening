def _valid_question_payload(position_id=None):
    return {
        "question_text": "Apakah anda merasa lelah?",
        "active": True,
        "position_ids": [position_id] if position_id else [],
        "options": [
            {"option_code": "A", "option_text": "Tidak pernah", "score": 0, "order_number": 0},
            {"option_code": "B", "option_text": "Kadang-kadang", "score": 1, "order_number": 1},
            {"option_code": "C", "option_text": "Sering", "score": 2, "order_number": 2},
            {"option_code": "D", "option_text": "Sangat sering", "score": 3, "order_number": 3},
        ],
    }


def test_create_question(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = client.post("/api/admin/questions", headers=headers, json=_valid_question_payload())
    assert r.status_code == 201
    assert len(r.json()["options"]) == 4


def test_create_question_missing_option_rejected(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = _valid_question_payload()
    payload["options"] = payload["options"][:3]  # only 3 options, missing D
    r = client.post("/api/admin/questions", headers=headers, json=payload)
    assert r.status_code == 422


def test_update_question(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = client.post("/api/admin/questions", headers=headers, json=_valid_question_payload())
    qid = r.json()["id"]
    r = client.put(f"/api/admin/questions/{qid}", headers=headers, json={"question_text": "Updated text"})
    assert r.status_code == 200
    assert r.json()["question_text"] == "Updated text"


def test_deactivate_question(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = client.post("/api/admin/questions", headers=headers, json=_valid_question_payload())
    qid = r.json()["id"]
    r = client.put(f"/api/admin/questions/{qid}", headers=headers, json={"active": False})
    assert r.status_code == 200
    assert r.json()["active"] is False


def test_delete_question(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = client.post("/api/admin/questions", headers=headers, json=_valid_question_payload())
    qid = r.json()["id"]
    r = client.delete(f"/api/admin/questions/{qid}", headers=headers)
    assert r.status_code == 200
    r = client.get(f"/api/admin/questions/{qid}", headers=headers)
    assert r.status_code == 404


def test_get_nonexistent_question(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = client.get("/api/admin/questions/00000000-0000-0000-0000-000000000000", headers=headers)
    assert r.status_code == 404
    assert r.json()["error_code"] == "QUESTION_NOT_FOUND"
