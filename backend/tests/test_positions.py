def test_create_position(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = client.post("/api/admin/positions", headers=headers, json={"nama_jabatan": "Analyst"})
    assert r.status_code == 201
    assert r.json()["question_count"] == 0


def test_create_duplicate_position_rejected(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    client.post("/api/admin/positions", headers=headers, json={"nama_jabatan": "Auditor"})
    r = client.post("/api/admin/positions", headers=headers, json={"nama_jabatan": "auditor"})
    assert r.status_code == 409


def test_update_position(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = client.post("/api/admin/positions", headers=headers, json={"nama_jabatan": "OldName"})
    pid = r.json()["id"]
    r = client.put(f"/api/admin/positions/{pid}", headers=headers, json={"nama_jabatan": "NewName"})
    assert r.status_code == 200
    assert r.json()["nama_jabatan"] == "NewName"


def test_delete_position(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = client.post("/api/admin/positions", headers=headers, json={"nama_jabatan": "ToDelete"})
    pid = r.json()["id"]
    r = client.delete(f"/api/admin/positions/{pid}", headers=headers)
    assert r.status_code == 200
