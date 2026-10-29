"""
Seed script.

TEST DATA ONLY.
Replace with validated psychological instrument configuration before production use.

Usage:
    python -m app.seed
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.models import (
    Position, Question, AnswerOption, PositionQuestion, ResultCategory, Admin, AdminRole,
)


def seed():
    db = SessionLocal()
    try:
        # --- Admin bootstrap (from env, never hardcoded credentials) ---
        seed_admin_user = os.getenv("SEED_ADMIN_USERNAME", "superadmin")
        seed_admin_pass = os.getenv("SEED_ADMIN_PASSWORD")
        if not db.query(Admin).filter(Admin.username == seed_admin_user).first():
            if not seed_admin_pass:
                print(
                    "PERINGATAN: SEED_ADMIN_PASSWORD tidak diset di environment. "
                    "Admin default TIDAK dibuat. Set env var lalu jalankan ulang seed, "
                    "atau buat admin lewat script create_admin.py."
                )
            else:
                admin = Admin(
                    username=seed_admin_user,
                    password_hash=hash_password(seed_admin_pass),
                    role=AdminRole.superadmin,
                )
                db.add(admin)
                print(f"Admin superadmin '{seed_admin_user}' dibuat.")

        # --- Positions (contoh jabatan) ---
        position_names = ["Staff", "Supervisor", "Manager", "HR", "IT", "Finance"]
        positions = {}
        for name in position_names:
            pos = db.query(Position).filter(Position.nama_jabatan == name).first()
            if not pos:
                pos = Position(nama_jabatan=name, description=f"Jabatan {name} (data testing)", active=True)
                db.add(pos)
                db.flush()
            positions[name] = pos

        db.commit()

        # --- Result categories (TEST DATA ONLY) ---
        if db.query(ResultCategory).count() == 0:
            categories = [
                ("Normal", 0, 10,
                 "Kondisi psikologis Anda saat ini berada dalam rentang normal.",
                 "Tetap jaga keseimbangan kerja dan istirahat."),
                ("Stres Ringan", 11, 20,
                 "Anda menunjukkan indikasi stres ringan.",
                 "Perhatikan pola istirahat dan beban kerja Anda."),
                ("Stres Sedang", 21, 30,
                 "Anda menunjukkan indikasi stres sedang.",
                 "Disarankan berkonsultasi dengan atasan atau tim HR terkait beban kerja."),
                ("Stres Tinggi", 31, 999,
                 "Anda menunjukkan indikasi stres tinggi.",
                 "Disarankan segera berkonsultasi dengan psikolog/profesional kesehatan mental."),
            ]
            for name, mn, mx, msg, rec in categories:
                db.add(ResultCategory(name=name, min_score=mn, max_score=mx, message=msg,
                                       recommendation=rec, active=True))
            db.commit()
            print("Kategori hasil (TEST DATA ONLY) dibuat.")

        # --- Questions (contoh, dummy untuk testing) ---
        if db.query(Question).count() == 0:
            base_questions = [
                "Saya merasa terbebani oleh pekerjaan saya.",
                "Saya kesulitan tidur karena memikirkan pekerjaan.",
                "Saya merasa didukung oleh rekan kerja saya.",
                "Saya merasa mampu menyelesaikan tugas tepat waktu.",
                "Saya merasa cemas menjelang jam kerja.",
                "Saya merasa dihargai atas kontribusi saya di tempat kerja.",
                "Saya sulit berkonsentrasi saat bekerja.",
                "Saya merasa memiliki keseimbangan antara pekerjaan dan kehidupan pribadi.",
                "Saya merasa mudah marah/tersinggung akhir-akhir ini.",
                "Saya merasa optimis terhadap karier saya.",
            ]
            option_template = [
                ("A", "Tidak pernah", 0),
                ("B", "Kadang-kadang", 1),
                ("C", "Sering", 2),
                ("D", "Sangat sering", 3),
            ]

            all_questions = []
            for text in base_questions:
                q = Question(question_text=text, active=True)
                db.add(q)
                db.flush()
                for code, label, score in option_template:
                    db.add(AnswerOption(question_id=q.id, option_code=code, option_text=label,
                                         score=score, order_number=ord(code) - ord("A")))
                all_questions.append(q)
            db.commit()

            # Mapping jabatan -> jumlah pertanyaan berbeda (sesuai requirement, tidak fixed)
            mapping_plan = {
                "Staff": all_questions[:4],
                "Supervisor": all_questions[:7],
                "Manager": all_questions[:10],
                "HR": all_questions[2:8],
                "IT": all_questions[0:6],
                "Finance": all_questions[1:9],
            }
            for pos_name, qs in mapping_plan.items():
                for idx, q in enumerate(qs):
                    db.add(PositionQuestion(position_id=positions[pos_name].id, question_id=q.id, order_number=idx))
            db.commit()
            print(f"{len(all_questions)} pertanyaan contoh (TEST DATA ONLY) dibuat dan dipetakan ke jabatan.")

        print("Seed selesai.")
    finally:
        db.close()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)  # no-op if alembic already ran; safe guard for fresh DB
    seed()
