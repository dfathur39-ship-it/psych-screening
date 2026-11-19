"""Aturan identitas peserta.

- Satu orang = satu akun. Nama tidak boleh dipakai dua akun berbeda, dan NIK hanya boleh milik satu akun.
- Mendaftar ulang dengan data yang persis sama masuk ke akun yang sama (bukan membuat akun baru).
- Data diri harus sama dengan KTP: nama sama, dan usia sama dengan usia yang dihitung dari tanggal lahir di KTP.
"""
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.errors import bad_request, conflict
from app.models.models import Participant

WIB = ZoneInfo("Asia/Jakarta")
_DATE_RE = re.compile(r"^(\d{2})[-/](\d{2})[-/](\d{4})$")


def clean_spaces(value: str) -> str:
    """Rapikan spasi ganda: 'Mira   Setiawan ' -> 'Mira Setiawan'."""
    return re.sub(r"\s+", " ", value or "").strip()


def name_key(value: str) -> str:
    """Kunci pembanding nama: huruf kecil, tanpa tanda baca, spasi dirapikan."""
    lowered = clean_spaces(value).lower()
    return clean_spaces(re.sub(r"[^a-z0-9 ]", "", lowered))


def phone_key(value: str) -> str:
    """Nomor HP dibandingkan sebagai angka saja, dengan awalan +62/62 disamakan dengan 0."""
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("62"):
        digits = "0" + digits[2:]
    return digits


def today_wib() -> date:
    return datetime.now(WIB).date()


def parse_birth_date(value: str) -> date:
    m = _DATE_RE.match((value or "").strip())
    if not m:
        raise bad_request("Tanggal lahir tidak valid", "TANGGAL_LAHIR_TIDAK_VALID")
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        born = date(year, month, day)
    except ValueError:
        raise bad_request("Tanggal lahir tidak valid", "TANGGAL_LAHIR_TIDAK_VALID") from None
    if born > today_wib():
        raise bad_request("Tanggal lahir tidak boleh di masa depan", "TANGGAL_LAHIR_TIDAK_VALID")
    return born


def age_on(born: date, today: date | None = None) -> int:
    today = today or today_wib()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def find_by_name(db: Session, nama: str) -> Participant | None:
    """Cari akun dengan nama yang sama (tanpa membedakan huruf besar/kecil, spasi, dan tanda baca)."""
    key = name_key(nama)
    if not key:
        return None
    for pid, existing_name in db.query(Participant.id, Participant.nama).all():
        if name_key(existing_name) == key:
            return db.get(Participant, pid)
    return None


def match_existing_account(existing: Participant, *, email: str, no_hp: str, usia: int, jabatan: str) -> bool:
    """True bila semua data diri sama dengan akun yang sudah ada."""
    return (
        (existing.email or "").strip().lower() == (email or "").strip().lower()
        and phone_key(existing.no_hp) == phone_key(no_hp)
        and existing.usia == usia
        and clean_spaces(existing.jabatan).lower() == clean_spaces(jabatan).lower()
    )


def ensure_ktp_matches_profile(participant: Participant, *, nama_ktp: str, tanggal_lahir: str) -> int:
    """Pastikan nama dan usia di KTP sama dengan data diri. Mengembalikan usia dari KTP."""
    if name_key(nama_ktp) != name_key(participant.nama):
        raise bad_request(
            f'Nama di KTP ("{clean_spaces(nama_ktp)}") tidak sama dengan data dirimu ("{participant.nama}"). '
            "Samakan dulu supaya bisa disimpan.",
            "NAMA_TIDAK_SAMA",
        )
    age = age_on(parse_birth_date(tanggal_lahir))
    if age != participant.usia:
        raise bad_request(
            f"Usia dari tanggal lahir di KTP adalah {age} tahun, sedangkan di data dirimu {participant.usia} tahun. "
            "Usia harus sama.",
            "USIA_TIDAK_SAMA",
        )
    return age


def ensure_nik_available(db: Session, participant: Participant, nik: str) -> None:
    other = db.query(Participant).filter(Participant.nik == nik, Participant.id != participant.id).first()
    if other:
        raise conflict(
            "NIK ini sudah terdaftar pada akun lain. Satu KTP hanya bisa dipakai oleh satu akun.",
            "NIK_SUDAH_TERDAFTAR",
        )
