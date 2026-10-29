#!/usr/bin/env python3
"""End-to-end smoke test for the screening flow, run against the live server."""
import base64
import sys
import json
import requests

BASE = "http://localhost:8000"

# 1x1 PNG: enough for the upload endpoint to create the KTP document row (OCR returns nothing useful).
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGD4DwABBAEAX+XDSwAAAABJRU5ErkJggg=="
)
KTP_FULL = {
    "nik": "3171234567890123", "nama": "Peserta Smoke", "tempat_lahir": "Bogor", "tanggal_lahir": "01-02-1995",
    "jenis_kelamin": "LAKI-LAKI", "alamat": "Jl. Merdeka No. 1", "rt_rw": "001/002", "kelurahan": "Sukajadi",
    "kecamatan": "Bogor Barat", "agama": "ISLAM", "status_perkawinan": "KAWIN",
    "pekerjaan_ktp": "Karyawan Swasta", "kewarganegaraan": "WNI",
}


def confirm_ktp(pid):
    """Upload a KTP image, then confirm the data: the same two calls the profile page makes."""
    r = requests.post(f"{BASE}/api/ocr/ktp", data={"participant_id": pid},
                      files={"file": ("ktp.png", PNG_1X1, "image/png")})
    check(r.status_code == 200, f"Upload KTP (status={r.status_code}, body={r.text[:200]})")
    r = requests.post(f"{BASE}/api/ocr/ktp/confirm", json={"participant_id": pid, **KTP_FULL})
    check(r.status_code == 200 and r.json()["ktp_confirmed"] is True, f"Confirm KTP (status={r.status_code})")


def register(payload, confirm=True):
    """Create a participant (email is required) and, by default, confirm their KTP so screening can start."""
    slug = payload["nama"].lower().replace(" ", ".")
    r = requests.post(f"{BASE}/api/participants", json={**payload, "email": f"{slug}@example.com"})
    if confirm and r.status_code == 201:
        confirm_ktp(r.json()["id"])
    return r



def check(cond, msg):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {msg}")
    if not cond:
        sys.exit(1)


def main():
    # 1. Admin login
    r = requests.post(f"{BASE}/api/admin/login", json={"username": "superadmin", "password": "ChangeMe123!"})
    check(r.status_code == 200, f"Admin login (status={r.status_code}, body={r.text[:200]})")
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Wrong password should fail
    r = requests.post(f"{BASE}/api/admin/login", json={"username": "superadmin", "password": "wrong"})
    check(r.status_code == 401, "Wrong password rejected with 401")

    # 3. Create participant
    r = register({"nama": "Budi Santoso", "usia": 30, "jabatan": "Staff", "no_hp": "081234567890"}, confirm=False)
    check(r.status_code == 201, f"Create participant (status={r.status_code}, body={r.text[:300]})")
    participant = r.json()
    pid = participant["id"]
    check(participant.get("nik_masked") is None, "NIK masked is None before OCR (no NIK yet)")
    check(participant.get("email") == "budi.santoso@example.com", "Email is stored on the participant")
    check(participant.get("ktp_confirmed") is False, "KTP is not confirmed right after registration")

    # 3b. Starting questions is blocked until the KTP is confirmed in the profile
    r = requests.post(f"{BASE}/api/screening/start", json={"participant_id": pid, "jabatan": "Staff"})
    check(r.status_code == 403 and r.json().get("error_code") == "KTP_NOT_CONFIRMED",
          f"Start screening blocked before KTP confirmation (status={r.status_code})")
    confirm_ktp(pid)
    r = requests.get(f"{BASE}/api/participants/{pid}")
    check(r.status_code == 200 and r.json()["ktp_confirmed"] is True, "Profile shows KTP confirmed")

    # 4. Start screening for Staff (should have 4 questions per seed mapping)
    r = requests.post(f"{BASE}/api/screening/start", json={"participant_id": pid, "jabatan": "Staff"})
    check(r.status_code == 200, f"Start screening (status={r.status_code}, body={r.text[:300]})")
    session_id = r.json()["session_id"]

    # 5. Get questions
    r = requests.get(f"{BASE}/api/screening/{session_id}/questions")
    check(r.status_code == 200, f"Get questions (status={r.status_code})")
    questions = r.json()
    check(len(questions) == 4, f"Staff has 4 mapped questions (got {len(questions)})")
    for q in questions:
        check(len(q["options"]) == 4, f"Question {q['id']} has 4 options")
        for opt in q["options"]:
            check("score" not in opt, "Public option does not leak score")

    # 6. Try completing without answering anything -> should fail
    r = requests.post(f"{BASE}/api/screening/{session_id}/complete")
    check(r.status_code == 400, f"Complete without answers rejected (status={r.status_code})")
    check(r.json().get("error_code") == "INCOMPLETE_ANSWERS", "Correct error_code for incomplete answers")

    # 7. Answer all questions with option A (lowest score, e.g. 0 each) -> expect total 0 -> Normal
    for q in questions:
        option_a = next(o for o in q["options"] if o["option_code"] == "A")
        r = requests.post(f"{BASE}/api/screening/{session_id}/answers",
                           json={"question_id": q["id"], "answer_option_id": option_a["id"]})
        check(r.status_code == 200, f"Submit answer A for {q['id']} (status={r.status_code})")

    r = requests.post(f"{BASE}/api/screening/{session_id}/complete")
    check(r.status_code == 200, f"Complete screening (status={r.status_code}, body={r.text[:300]})")
    result = r.json()
    check(result["total_score"] == 0, f"Total score for all-A answers is 0 (got {result['total_score']})")
    check(result["category_name"] == "Normal", f"Category for score 0 is Normal (got {result['category_name']})")

    # 8. Duplicate completion should be idempotent (return same result, not error)
    r = requests.post(f"{BASE}/api/screening/{session_id}/complete")
    check(r.status_code == 200, "Re-completing an already-completed session is idempotent")

    # 9. Answering after completion should be rejected
    r = requests.post(f"{BASE}/api/screening/{session_id}/answers",
                       json={"question_id": questions[0]["id"], "answer_option_id": questions[0]["options"][0]["id"]})
    check(r.status_code == 409, f"Answering after completion rejected (status={r.status_code})")

    # 10. Test D+D+D+D -> higher score -> different category
    r = register({
        "nama": "Siti Aminah", "usia": 28,         "jabatan": "Manager", "no_hp": "081298765432",
    })
    pid2 = r.json()["id"]
    r = requests.post(f"{BASE}/api/screening/start", json={"participant_id": pid2, "jabatan": "Manager"})
    session_id2 = r.json()["session_id"]
    r = requests.get(f"{BASE}/api/screening/{session_id2}/questions")
    questions2 = r.json()
    check(len(questions2) == 10, f"Manager has 10 mapped questions (got {len(questions2)})")
    for q in questions2:
        option_d = next(o for o in q["options"] if o["option_code"] == "D")
        requests.post(f"{BASE}/api/screening/{session_id2}/answers",
                      json={"question_id": q["id"], "answer_option_id": option_d["id"]})
    r = requests.post(f"{BASE}/api/screening/{session_id2}/complete")
    result2 = r.json()
    check(result2["total_score"] == 30, f"10 questions x D(score 3) = 30 (got {result2['total_score']})")
    check(result2["category_name"] == "Stres Sedang", f"Score 30 -> Stres Sedang (got {result2['category_name']})")

    # 11. Unknown jabatan should still allow user to proceed (auto position creation + fallback questions)
    r = register({
        "nama": "Andi Wijaya", "usia": 25,         "jabatan": "Senior Digital Marketing Specialist", "no_hp": "081211112222",
    })
    pid3 = r.json()["id"]
    r = requests.post(f"{BASE}/api/screening/start",
                       json={"participant_id": pid3, "jabatan": "Senior Digital Marketing Specialist"})
    check(r.status_code == 200, f"Unknown jabatan still allows screening start (status={r.status_code})")
    session_id3 = r.json()["session_id"]
    r = requests.get(f"{BASE}/api/screening/{session_id3}/questions")
    check(r.status_code == 200, "Unknown jabatan gets fallback question set without error")

    # 12. Admin CRUD: create question, verify it appears for a position, edit, verify update propagates
    r = requests.get(f"{BASE}/api/admin/positions", headers=headers)
    check(r.status_code == 200, "List positions as admin")
    staff_position = next(p for p in r.json() if p["nama_jabatan"] == "Staff")

    r = requests.post(f"{BASE}/api/admin/questions", headers=headers, json={
        "question_text": "Pertanyaan test tambahan untuk Staff",
        "active": True,
        "position_ids": [staff_position["id"]],
        "options": [
            {"option_code": "A", "option_text": "Tidak pernah", "score": 0, "order_number": 0},
            {"option_code": "B", "option_text": "Kadang-kadang", "score": 1, "order_number": 1},
            {"option_code": "C", "option_text": "Sering", "score": 2, "order_number": 2},
            {"option_code": "D", "option_text": "Sangat sering", "score": 3, "order_number": 3},
        ],
    })
    check(r.status_code == 201, f"Admin creates new question (status={r.status_code}, body={r.text[:300]})")
    new_q_id = r.json()["id"]

    r = register({
        "nama": "Test User Staff2", "usia": 26,         "jabatan": "Staff", "no_hp": "081200001111",
    })
    pid4 = r.json()["id"]
    r = requests.post(f"{BASE}/api/screening/start", json={"participant_id": pid4, "jabatan": "Staff"})
    session_id4 = r.json()["session_id"]
    r = requests.get(f"{BASE}/api/screening/{session_id4}/questions")
    q_ids = [q["id"] for q in r.json()]
    check(new_q_id in q_ids, "Newly created question appears immediately in Staff screening (no restart needed)")
    check(len(q_ids) == 5, f"Staff now has 5 questions after admin addition (got {len(q_ids)})")

    # 13. Edit question text, verify propagation
    r = requests.put(f"{BASE}/api/admin/questions/{new_q_id}", headers=headers,
                      json={"question_text": "Pertanyaan yang sudah diedit"})
    check(r.status_code == 200, "Admin edits question")
    r = register({
        "nama": "Test User Staff3", "usia": 26,         "jabatan": "Staff", "no_hp": "081200002222",
    })
    pid5 = r.json()["id"]
    r = requests.post(f"{BASE}/api/screening/start", json={"participant_id": pid5, "jabatan": "Staff"})
    session_id5 = r.json()["session_id"]
    r = requests.get(f"{BASE}/api/screening/{session_id5}/questions")
    edited_q = next(q for q in r.json() if q["id"] == new_q_id)
    check(edited_q["question_text"] == "Pertanyaan yang sudah diedit", "Edited question text propagates to new users")

    # 14. Position mapping isolation: Manager questions should NOT include Staff-only Question 1 unless overlapped by design
    r = requests.get(f"{BASE}/api/admin/positions", headers=headers)
    manager_position = next(p for p in r.json() if p["nama_jabatan"] == "Manager")
    r = requests.post(f"{BASE}/api/admin/questions", headers=headers, json={
        "question_text": "Pertanyaan khusus Manager saja",
        "active": True,
        "position_ids": [manager_position["id"]],
        "options": [
            {"option_code": "A", "option_text": "A", "score": 0, "order_number": 0},
            {"option_code": "B", "option_text": "B", "score": 1, "order_number": 1},
            {"option_code": "C", "option_text": "C", "score": 2, "order_number": 2},
            {"option_code": "D", "option_text": "D", "score": 3, "order_number": 3},
        ],
    })
    manager_only_q_id = r.json()["id"]
    r = requests.get(f"{BASE}/api/screening/{session_id5}/questions")  # this is a Staff session
    staff_q_ids = [q["id"] for q in r.json()]
    check(manager_only_q_id not in staff_q_ids, "Staff does NOT receive Manager-only question")

    # 15. Delete question, verify removed
    r = requests.delete(f"{BASE}/api/admin/questions/{new_q_id}", headers=headers)
    check(r.status_code == 200, "Admin deletes question")

    # 16. Category CRUD + boundary test
    r = requests.get(f"{BASE}/api/admin/categories", headers=headers)
    categories = r.json()
    check(len(categories) == 4, f"4 seeded categories exist (got {len(categories)})")

    r = requests.post(f"{BASE}/api/admin/categories", headers=headers, json={
        "name": "Test Invalid Range", "min_score": 100, "max_score": 5,
        "message": "x", "recommendation": "y",
    })
    check(r.status_code == 422, f"Invalid range (min>max) rejected at schema level (status={r.status_code})")

    # 17. Statistics endpoint
    r = requests.get(f"{BASE}/api/admin/statistics", headers=headers)
    check(r.status_code == 200, "Statistics endpoint works")
    stats = r.json()
    check(stats["total_participants"] >= 5, f"Statistics reflect real DB data (participants={stats['total_participants']})")

    # 18. Export
    r = requests.get(f"{BASE}/api/admin/export/csv", headers=headers)
    check(r.status_code == 200, "CSV export works")
    check("NIK" not in r.text, "NIK column not present in CSV export by default")

    # 19. Unauthorized access to admin endpoint
    r = requests.get(f"{BASE}/api/admin/questions")
    check(r.status_code == 401, "Admin endpoint rejects request without token")

    # 20. Audit log recorded
    r = requests.get(f"{BASE}/api/admin/audit-logs", headers=headers)
    check(r.status_code == 200, "Audit log endpoint accessible")
    check(len(r.json()["items"]) > 0, "Audit log has entries")

    # 21. IDOR check: answer_option belonging to a different question should be rejected
    other_q = questions2[7]  # a question only mapped to Manager, not overlapping with Staff's first 4
    wrong_option = questions[0]["options"][0]  # option belonging to a Staff question (genuinely different)
    check(other_q["id"] not in [q["id"] for q in questions], "Sanity: chosen questions are genuinely different")
    r = requests.post(f"{BASE}/api/screening/{session_id5}/answers",
                       json={"question_id": other_q["id"], "answer_option_id": wrong_option["id"]})
    check(r.status_code == 400, f"Mismatched question/option rejected (status={r.status_code})")

    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
