from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------- Common ----------
class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: str


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------- Participant ----------
class ParticipantCreate(BaseModel):
    nama: str = Field(min_length=2, max_length=255)
    usia: int = Field(ge=15, le=100)
    jabatan: str = Field(min_length=1, max_length=255)
    no_hp: str = Field(min_length=8, max_length=30)
    email: EmailStr = Field(max_length=255)

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, v):
        return str(v).strip().lower()

    @field_validator("no_hp")
    @classmethod
    def validate_phone(cls, v):
        digits = v.replace("+", "").replace("-", "").replace(" ", "")
        if not digits.isdigit():
            raise ValueError("Nomor HP tidak valid")
        return v


class ParticipantOut(BaseModel):
    id: str
    nama: str
    usia: int
    jabatan: str
    no_hp: str
    email: Optional[str] = None
    nik_masked: Optional[str] = None
    ktp_confirmed: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class ParticipantProfileOut(ParticipantOut):
    """Profil peserta + status skrining, dipakai halaman beranda dan profil."""
    in_progress_session_id: Optional[str] = None
    completed_session_id: Optional[str] = None
    # Status permintaan mengerjakan ulang yang masih berlaku (pending/approved/rejected),
    # None jika belum pernah minta atau permintaan terakhir sudah dipakai.
    retake_status: Optional[str] = None


# ---------- OCR / KTP ----------
class KtpOcrResult(BaseModel):
    success: bool
    ktp_document_id: Optional[str] = None
    nik: Optional[str] = None
    nama: Optional[str] = None
    tempat_lahir: Optional[str] = None
    tanggal_lahir: Optional[str] = None
    jenis_kelamin: Optional[str] = None
    alamat: Optional[str] = None
    rt_rw: Optional[str] = None
    kelurahan: Optional[str] = None
    kecamatan: Optional[str] = None
    agama: Optional[str] = None
    status_perkawinan: Optional[str] = None
    pekerjaan_ktp: Optional[str] = None
    kewarganegaraan: Optional[str] = None
    confidence: Optional[int] = None
    message: Optional[str] = None
    ocr_provider: Optional[str] = None  # tesseract | vlm (yang benar-benar dipakai)
    fallback_used: Optional[bool] = None
    auto_confirmed: Optional[bool] = None  # True bila langsung terkonfirmasi tanpa isi manual
    ktp_confirmed: Optional[bool] = None


class KtpConfirm(BaseModel):
    """Every KTP field is mandatory: the participant must review and complete all of them."""
    participant_id: str
    nik: str = Field(min_length=16, max_length=16)
    nama: str = Field(min_length=2, max_length=255)
    tempat_lahir: str = Field(min_length=2, max_length=255)
    tanggal_lahir: str = Field(pattern=r"^\d{2}[-/]\d{2}[-/]\d{4}$")
    jenis_kelamin: str = Field(min_length=1, max_length=20)
    alamat: str = Field(min_length=3, max_length=500)
    rt_rw: str = Field(min_length=1, max_length=20)
    kelurahan: str = Field(min_length=1, max_length=255)
    kecamatan: str = Field(min_length=1, max_length=255)
    agama: str = Field(min_length=1, max_length=50)
    status_perkawinan: str = Field(min_length=1, max_length=50)
    pekerjaan_ktp: str = Field(min_length=1, max_length=255)
    kewarganegaraan: str = Field(min_length=1, max_length=50)
    # Opsional: asal data (untuk audit). Diisi frontend setelah /api/ktp/scan; kosong = isi manual.
    scan_provider: Optional[str] = Field(default=None, max_length=20)
    scan_confidence: Optional[int] = Field(default=None, ge=0, le=100)

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("nik")
    @classmethod
    def validate_nik(cls, v):
        if not v.isdigit() or len(v) != 16:
            raise ValueError("NIK harus 16 digit angka")
        return v


# ---------- Position ----------
class PositionCreate(BaseModel):
    nama_jabatan: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    active: bool = True


class PositionUpdate(BaseModel):
    nama_jabatan: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    active: Optional[bool] = None


class PositionOut(BaseModel):
    id: str
    nama_jabatan: str
    description: Optional[str]
    active: bool
    question_count: Optional[int] = 0

    class Config:
        from_attributes = True


# ---------- Answer option ----------
class AnswerOptionCreate(BaseModel):
    option_code: str = Field(pattern="^[ABCD]$")
    option_text: str = Field(min_length=1)
    score: int
    order_number: int = 0


class AnswerOptionOut(BaseModel):
    id: str
    option_code: str
    option_text: str
    score: int
    order_number: int

    class Config:
        from_attributes = True


class AnswerOptionOutPublic(BaseModel):
    """Score hidden from public-facing endpoints to avoid leaking scoring weight to participants."""
    id: str
    option_code: str
    option_text: str
    order_number: int

    class Config:
        from_attributes = True


# ---------- Question ----------
class QuestionCreate(BaseModel):
    question_text: str = Field(min_length=1)
    active: bool = True
    position_ids: List[str] = Field(default_factory=list)
    options: List[AnswerOptionCreate] = Field(min_length=4, max_length=4)

    @field_validator("options")
    @classmethod
    def validate_options(cls, v):
        codes = sorted([o.option_code for o in v])
        if codes != ["A", "B", "C", "D"]:
            raise ValueError("Harus memiliki tepat 4 opsi: A, B, C, D")
        return v


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    active: Optional[bool] = None
    position_ids: Optional[List[str]] = None
    options: Optional[List[AnswerOptionCreate]] = None


class QuestionOut(BaseModel):
    id: str
    question_text: str
    active: bool
    options: List[AnswerOptionOut] = []
    position_ids: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionPublicOut(BaseModel):
    id: str
    question_text: str
    order_number: int
    options: List[AnswerOptionOutPublic]
    answered_option_id: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Result category ----------
class ResultCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    min_score: int
    max_score: int
    message: str
    recommendation: str
    active: bool = True

    @field_validator("max_score")
    @classmethod
    def validate_range(cls, v, info):
        min_score = info.data.get("min_score")
        if min_score is not None and v < min_score:
            raise ValueError("max_score harus >= min_score")
        return v


class ResultCategoryUpdate(BaseModel):
    name: Optional[str] = None
    min_score: Optional[int] = None
    max_score: Optional[int] = None
    message: Optional[str] = None
    recommendation: Optional[str] = None
    active: Optional[bool] = None


class ResultCategoryOut(BaseModel):
    id: str
    name: str
    min_score: int
    max_score: int
    message: str
    recommendation: str
    active: bool

    class Config:
        from_attributes = True


# ---------- Screening ----------
class ScreeningStart(BaseModel):
    participant_id: str
    jabatan: str


class ScreeningAnswerSubmit(BaseModel):
    question_id: str
    answer_option_id: str


class ScreeningResultOut(BaseModel):
    session_id: str
    total_score: int
    category_name: Optional[str]
    message: Optional[str]
    recommendation: Optional[str]
    disclaimer: str = (
        "Hasil ini merupakan hasil skrining dan bukan diagnosis psikologis atau diagnosis medis."
    )


# ---------- Admin auth ----------
class AdminLogin(BaseModel):
    username: str
    password: str


class AdminTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class AdminOut(BaseModel):
    id: str
    username: str
    role: str
    active: bool

    class Config:
        from_attributes = True


class AdminCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="admin")


# ---------- Support chat ----------
def _clean_text(v: str) -> str:
    v = (v or "").strip()
    if not v:
        raise ValueError("Tidak boleh kosong")
    return v


class RetakeRequestCreate(BaseModel):
    """Diajukan peserta lewat profilnya sendiri; tidak perlu mengetik ulang identitas."""
    reason: Optional[str] = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def _v_reason(cls, v):
        v = (v or "").strip()
        return v or None


class RetakeRequestOut(BaseModel):
    id: str
    status: str
    reason: Optional[str] = None
    admin_note: Optional[str] = None
    created_at: datetime
    decided_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RetakeDecision(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    admin_note: Optional[str] = Field(default=None, max_length=500)


class AdminRetakeRequestOut(BaseModel):
    id: str
    participant_id: str
    participant_nama: str
    participant_jabatan: str
    participant_no_hp: str
    participant_email: Optional[str] = None
    reason: Optional[str] = None
    status: str
    admin_note: Optional[str] = None
    created_at: datetime
    decided_at: Optional[datetime] = None


class SupportThreadCreate(BaseModel):
    """Pengirim adalah peserta yang sudah mengisi data diri; nama dan kontak diambil dari data itu."""
    participant_id: str
    message: str = Field(min_length=1, max_length=2000)

    _v_message = field_validator("message")(lambda cls, v: _clean_text(v))


class SupportMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)

    _v_body = field_validator("body")(lambda cls, v: _clean_text(v))


class SupportStatusUpdate(BaseModel):
    status: str = Field(pattern="^(open|closed)$")


class SupportMessageOut(BaseModel):
    id: str
    sender: str
    body: str
    created_at: datetime

    class Config:
        from_attributes = True
