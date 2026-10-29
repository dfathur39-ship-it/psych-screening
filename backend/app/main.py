import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.limiter import limiter
from app.routes import (
    participants, ocr, screening,
    admin_auth, admin_questions, admin_positions, admin_categories,
    admin_data, admin_statistics, admin_audit, admin_export, admin_management,
    support, admin_support, admin_retake, ktp_scan,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app")

app = FastAPI(title="API Skrining Psikologi Karyawan", version="1.0.0")
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={
        "success": False, "message": "Terlalu banyak permintaan. Coba lagi sebentar lagi.",
        "error_code": "RATE_LIMITED",
    })


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "success" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(status_code=exc.status_code, content={
        "success": False, "message": str(detail), "error_code": "HTTP_ERROR",
    })


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    message = "; ".join(f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in errors)
    return JSONResponse(status_code=422, content={
        "success": False, "message": message or "Data tidak valid", "error_code": "VALIDATION_ERROR",
    })


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak stack traces or internals to the client.
    logger.exception(f"Unhandled error on {request.method} {request.url.path}")
    return JSONResponse(status_code=500, content={
        "success": False, "message": "Terjadi kesalahan pada server", "error_code": "INTERNAL_SERVER_ERROR",
    })


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(participants.router)
app.include_router(ocr.router)
app.include_router(ktp_scan.router)
app.include_router(screening.router)
app.include_router(admin_auth.router)
app.include_router(admin_questions.router)
app.include_router(admin_positions.router)
app.include_router(admin_categories.router)
app.include_router(admin_data.router)
app.include_router(admin_statistics.router)
app.include_router(admin_audit.router)
app.include_router(admin_export.router)
app.include_router(admin_management.router)
app.include_router(support.router)
app.include_router(admin_support.router)
app.include_router(admin_retake.router)
