"""Skema request/response untuk POST /api/ktp/scan (tampil di Swagger /docs)."""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class KtpScanData(BaseModel):
    nik: Optional[str] = None
    nama: Optional[str] = None
    tempat_lahir: Optional[str] = None
    tanggal_lahir: Optional[str] = Field(default=None, description="Format YYYY-MM-DD")
    jenis_kelamin: Optional[str] = None
    alamat: Optional[str] = None
    rt_rw: Optional[str] = None
    kelurahan: Optional[str] = None
    kecamatan: Optional[str] = None
    agama: Optional[str] = None
    status_perkawinan: Optional[str] = None
    pekerjaan: Optional[str] = None
    kewarganegaraan: Optional[str] = None


class KtpScanResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
    data: KtpScanData
    confidence: Dict[str, Optional[float]] = Field(description="Confidence per field, 0.0-1.0")
    field_status: Dict[str, str] = Field(description="ok | review | unreadable, per field")
    needs_review: List[str] = Field(description="Field yang wajib diperiksa user (status bukan ok)")
    warnings: List[str] = []
    overall_confidence: Optional[float] = None
    confidence_threshold: float
    provider: str
    model: str
    fallback_used: bool = Field(default=False, description="True bila AI gagal/tidak tersedia lalu dipakai Tesseract")
    saved: bool = Field(default=False, description="Selalu false: hasil scan tidak disimpan sebelum user mengonfirmasi")


class KtpScanError(BaseModel):
    success: bool = False
    message: str
    error_code: str
    can_fill_manually: bool = True
