"""Ganti username/password admin sendiri: PUT /api/admin/me/profile."""
from app.core.security import hash_password
from app.models.models import Admin, AdminRole


def _admin(db, username="adm_prof", password="PasswordLama1"):
    a = Admin(username=username, password_hash=hash_password(password), role=AdminRole.admin, active=True)
    db.add(a)
    db.commit()
    return a


def _login(client, username, password):
    r = client.post("/api/admin/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_requires_auth(client):
    r = client.put("/api/admin/me/profile", json={"current_password": "x", "new_password": "PasswordBaru1"})
    assert r.status_code == 401


def test_wrong_current_password(client, db):
    _admin(db)
    h = _login(client, "adm_prof", "PasswordLama1")
    r = client.put("/api/admin/me/profile", headers=h, json={"current_password": "salah", "new_password": "PasswordBaru1"})
    assert r.status_code == 400
    assert r.json()["error_code"] == "INVALID_CURRENT_PASSWORD"


def test_change_password_then_login(client, db):
    _admin(db)
    h = _login(client, "adm_prof", "PasswordLama1")
    r = client.put("/api/admin/me/profile", headers=h, json={"current_password": "PasswordLama1", "new_password": "PasswordBaru1"})
    assert r.status_code == 200
    assert client.post("/api/admin/login", json={"username": "adm_prof", "password": "PasswordLama1"}).status_code == 401
    assert client.post("/api/admin/login", json={"username": "adm_prof", "password": "PasswordBaru1"}).status_code == 200


def test_change_username_and_conflict(client, db):
    _admin(db)
    _admin(db, "adm_lain")
    h = _login(client, "adm_prof", "PasswordLama1")
    r = client.put("/api/admin/me/profile", headers=h, json={"current_password": "PasswordLama1", "new_username": "adm_lain"})
    assert r.status_code == 409 and r.json()["error_code"] == "USERNAME_TAKEN"
    r = client.put("/api/admin/me/profile", headers=h, json={"current_password": "PasswordLama1", "new_username": "nama.baru"})
    assert r.status_code == 200 and r.json()["username"] == "nama.baru"
    assert client.post("/api/admin/login", json={"username": "nama.baru", "password": "PasswordLama1"}).status_code == 200


def test_validation(client, db):
    _admin(db)
    h = _login(client, "adm_prof", "PasswordLama1")
    base = {"current_password": "PasswordLama1"}
    assert client.put("/api/admin/me/profile", headers=h, json=base).status_code == 400  # tidak ada yang diubah
    assert client.put("/api/admin/me/profile", headers=h, json={**base, "new_password": "pendek"}).status_code == 422
    assert client.put("/api/admin/me/profile", headers=h, json={**base, "new_username": "a b!"}).status_code == 422
    assert client.put("/api/admin/me/profile", headers=h, json={**base, "new_password": "PasswordLama1"}).status_code == 400
