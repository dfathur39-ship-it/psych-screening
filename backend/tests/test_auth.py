def test_login_success(client, admin_token):
    assert admin_token is not None


def test_login_wrong_password(client, admin_token):
    r = client.post("/api/admin/login", json={"username": "testadmin", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["error_code"] == "INVALID_CREDENTIALS"


def test_login_nonexistent_user(client):
    r = client.post("/api/admin/login", json={"username": "ghost", "password": "whatever"})
    assert r.status_code == 401


def test_admin_endpoint_requires_token(client):
    r = client.get("/api/admin/questions")
    assert r.status_code == 401


def test_admin_endpoint_rejects_invalid_token(client):
    r = client.get("/api/admin/questions", headers={"Authorization": "Bearer garbage.token.here"})
    assert r.status_code == 401


def test_password_is_hashed_not_plaintext(db, admin_token):
    from app.models.models import Admin
    admin = db.query(Admin).filter(Admin.username == "testadmin").first()
    assert admin.password_hash != "TestPass123!"
    assert admin.password_hash.startswith("$argon2")
