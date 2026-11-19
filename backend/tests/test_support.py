from app.core.limiter import limiter

MESSAGE = "Halo, saya butuh bantuan"


def _participant(client, nama="Budi"):
    r = client.post("/api/participants", json={
        "nama": nama, "usia": 30, "jabatan": "Staff", "no_hp": "08123456789", "email": "budi@example.com"})
    assert r.status_code in (200, 201), r.text  # data yang sama masuk ke akun yang sama (200)
    return r.json()["id"]


def _create(client, participant_id=None, **over):
    body = {"participant_id": participant_id or _participant(client), "message": MESSAGE, **over}
    r = client.post("/api/support/threads", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _h(token):
    return {"X-Thread-Token": token}


def _auth(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def test_visitor_creates_thread_and_reads_messages(client):
    data = _create(client)
    assert data["token"] and data["thread_id"]
    assert data["messages"][0]["sender"] == "visitor"
    r = client.get(f"/api/support/threads/{data['thread_id']}/messages", headers=_h(data["token"]))
    assert r.status_code == 200
    assert [m["body"] for m in r.json()["messages"]] == ["Halo, saya butuh bantuan"]


def test_thread_requires_valid_token(client):
    data = _create(client)
    url = f"/api/support/threads/{data['thread_id']}/messages"
    assert client.get(url).status_code == 404  # no token
    assert client.get(url, headers=_h("salah")).status_code == 404  # wrong token
    other = _create(client, participant_id=_participant(client, "Orang Lain"))
    assert client.get(url, headers=_h(other["token"])).status_code == 404  # another visitor's token
    assert client.get("/api/support/threads/bukan-uuid/messages", headers=_h(data["token"])).status_code == 404


def test_token_is_not_stored_in_plaintext(client, db):
    from app.models.models import SupportThread
    data = _create(client)
    t = db.query(SupportThread).filter(SupportThread.id == data["thread_id"]).one()
    assert t.token_hash != data["token"] and len(t.token_hash) == 64


def test_validation_rejects_bad_input(client):
    pid = _participant(client)
    assert client.post("/api/support/threads", json={"participant_id": pid, "message": "   "}).status_code == 422
    assert client.post("/api/support/threads", json={"participant_id": pid, "message": "x" * 2001}).status_code == 422
    assert client.post("/api/support/threads", json={"message": MESSAGE}).status_code == 422
    data = _create(client)
    url = f"/api/support/threads/{data['thread_id']}/messages"
    assert client.post(url, json={"body": "  "}, headers=_h(data["token"])).status_code == 422


def test_admin_endpoints_require_auth(client):
    assert client.get("/api/admin/support/threads").status_code == 401
    assert client.get("/api/admin/support/unread-count").status_code == 401
    assert client.post("/api/admin/support/threads/x/messages", json={"body": "hi"}).status_code == 401


def test_full_conversation_flow(client, admin_token):
    data = _create(client)
    tid, tok = data["thread_id"], data["token"]

    # admin sees unread message
    r = client.get("/api/admin/support/unread-count", headers=_auth(admin_token))
    assert r.json() == {"unread_messages": 1, "unread_threads": 1}
    r = client.get("/api/admin/support/threads", headers=_auth(admin_token))
    item = r.json()["items"][0]
    assert item["unread_count"] == 1 and item["last_sender"] == "visitor" and item["visitor_name"] == "Budi"

    # opening the thread marks it read
    r = client.get(f"/api/admin/support/threads/{tid}", headers=_auth(admin_token))
    assert r.status_code == 200 and len(r.json()["messages"]) == 1
    assert client.get("/api/admin/support/unread-count", headers=_auth(admin_token)).json()["unread_messages"] == 0

    # admin replies; visitor sees it in order
    r = client.post(f"/api/admin/support/threads/{tid}/messages", json={"body": "Halo Budi"}, headers=_auth(admin_token))
    assert r.status_code == 201
    msgs = client.get(f"/api/support/threads/{tid}/messages", headers=_h(tok)).json()["messages"]
    assert [m["sender"] for m in msgs] == ["visitor", "admin"]

    # visitor answers
    r = client.post(f"/api/support/threads/{tid}/messages", json={"body": "Terima kasih"}, headers=_h(tok))
    assert r.status_code == 201
    assert [m["body"] for m in r.json()["messages"]] == ["Halo, saya butuh bantuan", "Halo Budi", "Terima kasih"]
    assert client.get("/api/admin/support/unread-count", headers=_auth(admin_token)).json()["unread_messages"] == 1


def test_close_blocks_visitor_messages(client, admin_token):
    data = _create(client)
    tid, tok = data["thread_id"], data["token"]
    r = client.put(f"/api/admin/support/threads/{tid}/status", json={"status": "closed"}, headers=_auth(admin_token))
    assert r.status_code == 200
    assert client.get(f"/api/support/threads/{tid}/messages", headers=_h(tok)).json()["status"] == "closed"
    closed = client.get("/api/admin/support/threads?status=closed", headers=_auth(admin_token)).json()
    assert closed["total"] == 1
    assert client.get("/api/admin/support/threads?status=open", headers=_auth(admin_token)).json()["total"] == 0

    # A closed thread cannot receive further visitor messages: they must start a new conversation.
    r = client.post(f"/api/support/threads/{tid}/messages", json={"body": "Masih butuh bantuan"}, headers=_h(tok))
    assert r.status_code == 409 and r.json()["error_code"] == "THREAD_CLOSED"
    assert client.get(f"/api/support/threads/{tid}/messages", headers=_h(tok)).json()["status"] == "closed"

    # Starting a new conversation (a fresh thread) still works.
    other = _create(client, participant_id=_participant(client, "Budi Lagi"))
    assert other["thread_id"] != tid

    assert client.put(f"/api/admin/support/threads/{tid}/status", json={"status": "bogus"}, headers=_auth(admin_token)).status_code == 422


def test_admin_can_still_reply_after_closing(client, admin_token):
    """Closing blocks the visitor, not the admin: an admin reply reopens the thread deliberately."""
    data = _create(client)
    tid, tok = data["thread_id"], data["token"]
    client.put(f"/api/admin/support/threads/{tid}/status", json={"status": "closed"}, headers=_auth(admin_token))
    r = client.post(f"/api/admin/support/threads/{tid}/messages", json={"body": "Ada tambahan?"}, headers=_auth(admin_token))
    assert r.status_code == 201
    assert client.get(f"/api/support/threads/{tid}/messages", headers=_h(tok)).json()["status"] == "open"


def test_admin_unknown_thread_is_404(client, admin_token):
    r = client.get("/api/admin/support/threads/does-not-exist", headers=_auth(admin_token))
    assert r.status_code == 404 and r.json()["error_code"] == "THREAD_NOT_FOUND"


def test_thread_creation_is_rate_limited(client):
    limiter.enabled = True
    limiter.reset()
    try:
        pid = _participant(client)
        codes = [client.post("/api/support/threads", json={"participant_id": pid, "message": MESSAGE}).status_code
                 for _ in range(7)]
        assert codes[:5] == [201] * 5 and 429 in codes[5:]
    finally:
        limiter.enabled = False
        limiter.reset()


def test_thread_takes_name_and_contact_from_data_diri(client, admin_token):
    _create(client, participant_id=_participant(client, "Siti Aminah"))
    item = client.get("/api/admin/support/threads", headers=_auth(admin_token)).json()["items"][0]
    assert item["visitor_name"] == "Siti Aminah"
    assert "budi@example.com" in item["visitor_contact"] and "08123456789" in item["visitor_contact"]


def test_thread_requires_registered_participant(client):
    for pid in ["00000000-0000-0000-0000-000000000000", "bukan-uuid"]:
        r = client.post("/api/support/threads", json={"participant_id": pid, "message": MESSAGE})
        assert r.status_code == 404 and r.json()["error_code"] == "PARTICIPANT_NOT_FOUND", pid
