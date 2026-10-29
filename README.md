# Skrining Psikologi Karyawan

Aplikasi web full-stack untuk skrining psikologi karyawan: peserta mengisi data diri,
memindai KTP (OCR), menjawab pertanyaan skrining sesuai jabatan (A/B/C/D), lalu
mendapatkan skor dan kategori hasil yang seluruhnya dihitung dan disimpan di backend.
Admin memiliki dashboard terpisah untuk mengelola pertanyaan, jabatan, kategori hasil,
peserta, dan audit log.

> **PENTING:** Data pertanyaan, skor, dan kategori hasil pada seed adalah **TEST DATA
> ONLY** untuk keperluan pengembangan/demo. Ganti dengan instrumen psikologi yang telah
> divalidasi sebelum digunakan secara resmi.

---

## Project Overview

| Layer     | Teknologi |
|-----------|-----------|
| Backend   | Python 3.12, FastAPI, SQLAlchemy, Alembic, Pydantic, JWT, Argon2 |
| Database  | PostgreSQL |
| Frontend  | React 19 + TypeScript + Vite, Axios, React Router, React Hook Form |
| OCR / VLM | Scan KTP dengan AI (Claude Vision / OpenAI-compatible / lokal) + Tesseract offline sebagai fallback |
| Deployment| Docker + Docker Compose |

## Architecture

```
Frontend (React/Vite)
      ↓  REST (axios)
FastAPI routes  (app/routes/*)
      ↓
Service layer   (app/services/*)  — scoring engine, OCR, position resolver, audit
      ↓
SQLAlchemy models (app/models/*)
      ↓
PostgreSQL
```

Business logic (scoring, position→question resolution, OCR parsing) lives entirely in
`app/services/`, never in routes and never in the frontend. The frontend only renders
what the backend returns.

## Requirements

- Python 3.12+
- Node.js 20+ (for local frontend dev without Docker)
- PostgreSQL 14+ (or use Docker Compose, which provisions it for you)
- Tesseract OCR with the Indonesian language pack, if running the backend outside Docker
  (`apt-get install tesseract-ocr tesseract-ocr-ind` on Debian/Ubuntu)
- Docker + Docker Compose (recommended, for the easiest full-stack run)

## Quick Start (Docker Compose — recommended)

```bash
cp .env.example .env
# Edit .env: set SECRET_KEY, JWT_SECRET (random strings), SEED_ADMIN_PASSWORD, etc.
# Generate strong secrets with: python3 -c "import secrets; print(secrets.token_urlsafe(48))"

docker compose up --build -d

# Run migrations (already run automatically on backend container start, but
# safe to re-run manually if needed):
docker compose exec backend alembic upgrade head

# Seed test data + bootstrap the first admin (reads SEED_ADMIN_USERNAME /
# SEED_ADMIN_PASSWORD from the backend container's environment — set them in
# your .env before running this):
docker compose exec backend python -m app.seed
```

- Frontend: http://localhost:8080
- Backend API docs (Swagger): http://localhost:8000/docs
- Admin login: http://localhost:8080/admin/login

## Manual Setup (without Docker)

### 1. Database

```bash
sudo -u postgres psql -c "CREATE DATABASE psych_screening;"
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
```

### 2. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your DATABASE_URL, SECRET_KEY, JWT_SECRET, etc.

alembic upgrade head

# Bootstrap admin + seed test data (env vars only needed for this one command):
SEED_ADMIN_USERNAME=superadmin SEED_ADMIN_PASSWORD='ChangeThisPassword!' python -m app.seed

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env   # sets VITE_API_URL=http://localhost:8000
npm run dev
```

Open http://localhost:5173.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|---|---|
| `DATABASE_URL` | SQLAlchemy PostgreSQL connection string |
| `SECRET_KEY` / `JWT_SECRET` | Random secrets — **never commit real values** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiry, default 60 |
| `CORS_ORIGINS` | Comma-separated allowed origins for the frontend |
| `OCR_PROVIDER` | `auto` (default, VLM utama) \\| `vlm` \\| `tesseract` |
| `OCR_API_KEY` | Only used if you plug in a paid/cloud OCR provider |
| `VLM_PROVIDER` | `anthropic` \| `openai` \| `local`. Kosong = otomatis (VLM_BASE_URL terisi -> openai; hanya ANTHROPIC_API_KEY -> anthropic) |
| `ANTHROPIC_API_KEY` | Kunci API Anthropic untuk Claude Vision — **jangan di-commit** |
| `VLM_MAX_TOKENS` | Batas token jawaban VLM, default 2048 |
| `VLM_CONFIDENCE_THRESHOLD` | Ambang confidence per field (0.0-1.0), default 0.80; di bawahnya ditandai ⚠ Periksa kembali |
| `MAX_KTP_FILE_SIZE_MB` | Batas ukuran foto untuk `/api/ktp/scan`, default 5 |
| `KTP_SCAN_RATE_LIMIT` / `KTP_SCAN_MAX_PER_PARTICIPANT` / `KTP_SCAN_WINDOW_S` / `KTP_SCAN_GLOBAL_MAX_PER_WINDOW` | Pagar pemakaian API: per IP, per peserta, dan global (default 10/minute, 8, 3600, 500) |
| `VLM_BASE_URL` / `VLM_API_KEY` / `VLM_MODEL` | OpenAI-compatible VLM (mis. `https://api.openai.com/v1` + `gpt-4o-mini`, atau Ollama `http://host.docker.internal:11434/v1` + `llava`). Kosong = fallback ke Tesseract |
| `VLM_TIMEOUT_S` | Timeout request VLM, default 30 |
| `VLM_AUTO_CONFIRM` | Alur lama `/api/ocr/ktp`. `false` (default): hasil AI selalu diperiksa user. `true` = menyimpan hasil AI tanpa dicek user (tidak disarankan) |
| `VLM_AUTO_CONFIRM_MIN_CONFIDENCE` | Minimal confidence (0-100) agar bisa auto-confirm, default 80 |
| `UPLOAD_DIR` | Private server-side path where KTP images are temporarily written before OCR |
| `KTP_RETENTION_DELETE_AFTER_OCR` | `true` (default) deletes the KTP image file immediately after OCR completes — only the extracted text fields are retained. Set `false` to keep the file in `UPLOAD_DIR` for audit purposes (never exposed via a public URL either way) |
| `MAX_UPLOAD_SIZE_MB` | Upload size limit for KTP images |

### Frontend (`frontend/.env`)

| Variable | Description |
|---|---|
| `VITE_API_URL` | Base URL of the backend API |

## Database Setup & Migration

Schema is fully managed by Alembic — no manual SQL required.

```bash
cd backend
alembic upgrade head        # apply all migrations
alembic revision --autogenerate -m "description"   # after changing models
```

## Seed Data

```bash
cd backend
SEED_ADMIN_USERNAME=superadmin SEED_ADMIN_PASSWORD='YourStrongPassword!' python -m app.seed
```

This creates:
- One `superadmin` account (password only from env var — never hardcoded)
- 6 example positions (Staff, Supervisor, Manager, HR, IT, Finance)
- 4 example result categories — **TEST DATA ONLY**, replace with a validated instrument
- 10 example questions with A/B/C/D options, mapped to positions with **different
  question counts per position** (Staff=4, Supervisor=7, Manager=10, etc.) to
  demonstrate that question sets are fully data-driven, not hardcoded

Re-running the seed script is idempotent for positions/admin (skips if they already
exist) but will skip category/question seeding entirely if any already exist, so it
won't duplicate data on a database that already has content.

## Alur peserta

Data diri (nama, usia, jabatan, nomor HP) -> foto KTP -> periksa data KTP -> pertanyaan -> hasil.

- **Semua 13 kolom KTP wajib diisi** di langkah konfirmasi, dan dicek juga di backend
  (`POST /api/ocr/ktp/confirm` menolak dengan 422 bila ada yang kosong atau formatnya salah:
  NIK 16 digit, tanggal lahir `DD-MM-YYYY`).
- Kolom **divisi sudah dihapus**; hanya jabatan yang dikumpulkan. Kolom `participants.divisi`
  masih ada di database (dibuat nullable oleh migration `participant divisi optional`) supaya data
  lama tidak hilang, tetapi tidak lagi diisi, ditampilkan, atau diekspor. Hapus kolomnya lewat
  migration baru jika data lama itu memang tidak diperlukan.
- Jawaban tersimpan setiap dipilih; setelah refresh peserta dilanjutkan dari pertanyaan yang belum dijawab.
- Di halaman pertanyaan: tombol A-D memilih jawaban, panah kiri/kanan pindah pertanyaan.

## Help & Contact (chat dengan admin)

- **/bantuan**: halaman FAQ dengan pencarian. Konten ada di `frontend/src/pages/public/Help.tsx`.
- **/kontak**: pengunjung mengirim pesan, lalu balasan admin muncul di halaman yang sama.
  Tidak perlu akun. Saat percakapan dibuat, server mengirim token rahasia acak yang disimpan
  di `localStorage` peramban; hanya hash SHA-256-nya yang disimpan di database. Token dikirim
  lewat header `X-Thread-Token`, jadi pengunjung hanya bisa membuka percakapannya sendiri.
- **Admin > Pesan** (`/admin/support`): inbox dua panel, badge jumlah pesan belum dibaca,
  balas, dan tandai selesai/buka lagi. Pesan baru dari pengunjung otomatis membuka kembali
  percakapan yang sudah selesai.
- Pembuatan percakapan dibatasi 5 per menit per IP, kirim pesan 30 per menit.
- Tabel baru: `support_threads` dan `support_messages`. **Jalankan `alembic upgrade head`
  setelah memperbarui kode** (Docker menjalankannya otomatis saat backend start).

Catatan: pesan diperbarui lewat polling (setiap 4-5 detik saat tab terbuka), bukan WebSocket.
Cukup untuk volume kecil sampai menengah; jika butuh notifikasi seketika, ganti polling di
`usePolling` dengan WebSocket/SSE tanpa mengubah tabel maupun endpoint yang ada.

## Running Tests

### Backend (pytest — 177 automated tests, termasuk 97 untuk scan KTP dengan VLM yang di-mock)

```bash
cd backend
source venv/bin/activate   # if not already active
pytest tests/ -v
```

Tests run against an isolated `psych_screening_test` database (created and dropped
automatically) and cover: authentication, participant creation & validation, question
CRUD, position CRUD & mapping isolation, the scoring engine (exact-sum tests, boundary
tests, overlapping-range resolution, no-match handling), the full screening session
lifecycle (start → answer → complete → result), and authorization checks.

### End-to-end smoke test (against a live running server)

```bash
cd backend
python scripts/smoke_test.py
```

Exercises the full stack against a real running instance (needs the backend + a
seeded database up), including the specific "critical feature" scenarios from the
spec: an admin-added question appearing immediately for new users without a restart,
position-based question isolation, and edited questions propagating to new sessions.

### Frontend

```bash
cd frontend
npm run build   # type-checks (tsc -b) and produces a production build
```

## Docker

`docker-compose.yml` at the repo root runs three services: `postgres`, `backend`
(FastAPI, runs `alembic upgrade head` automatically on container start), and
`frontend` (built and served via nginx). See **Quick Start** above.

## Admin Login

There is no hardcoded default admin. The first admin is created by the seed script,
reading credentials from environment variables:

```bash
SEED_ADMIN_USERNAME=superadmin SEED_ADMIN_PASSWORD='YourStrongPassword!' python -m app.seed
```

Additional admins can then be created by a `superadmin` via
`POST /api/admin/admins` (see API docs at `/docs`), never by editing source code.

## OCR Configuration

Default provider is **Tesseract OCR**, running fully offline/on-server (no external
API calls, no data leaves your infrastructure). It requires the `tesseract-ocr` and
`tesseract-ocr-ind` (Indonesian language data) system packages — already installed in
the backend Docker image.

OCR output is **never trusted as final**: it is returned to the frontend as an
editable draft, the user reviews/corrects every field, and only the confirmed data is
persisted (`POST /api/ocr/ktp/confirm`). If OCR fails to extract enough fields, the
user is told to complete the data manually rather than being blocked or shown
fabricated data.

To use a different OCR provider, implement the same function signature as
`run_ocr_on_image()` in `backend/app/services/ocr_service.py` and switch
`OCR_PROVIDER` — the rest of the pipeline is provider-agnostic.

### Scan KTP dengan AI (`POST /api/ktp/scan`)

`OCR_PROVIDER=auto` (default): AI dulu, otomatis Tesseract bila AI gagal/belum dikonfigurasi; `vlm` = hanya AI; `tesseract` = hanya Tesseract (gratis, akurasi terbatas, semua kolom ditandai ⚠).

Alur: upload foto -> validasi file -> preprocessing -> VLM -> validasi hasil (NIK 16 digit, tanggal,
confidence) -> **draft** dikirim ke frontend -> user memeriksa/mengoreksi -> `POST /api/ocr/ktp/confirm`
menyimpan ke PostgreSQL. Endpoint scan **tidak menyimpan gambar maupun hasilnya**. "Isi Manual" selalu
tersedia, dan tetap berfungsi bila AI gagal.

```bash
# backend/.env — Claude Vision
VLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...        # buat di https://console.anthropic.com/ -> Settings -> API Keys
VLM_MODEL=                          # kosong = claude-sonnet-5-5
```

Kode: `backend/app/services/vision/` (provider `anthropic`, `openai`, `local`), `ktp_image.py`,
`ktp_validation.py`, `routes/ktp_scan.py`. Respons berisi `data`, `confidence`, `field_status`
(`ok|review|unreadable`), `needs_review`, `warnings`. Kode error: 400 file tidak valid, 404 peserta,
413 terlalu besar, 422 bukan KTP/tidak terbaca, 429 rate limit/kuota, 502 respons AI rusak,
503 AI tidak tersedia/belum dikonfigurasi, 504 timeout. Semua error menyertakan `can_fill_manually`.
Kuota per peserta/global disimpan in-memory per proses (pakai Redis bila menjalankan banyak worker).

### VLM (alur lama `/api/ocr/ktp`)

Alternatif OCR yang lebih akurat via API OpenAI-compatible (`backend/app/services/vlm_service.py`):

```bash
# .env — contoh OpenAI
OCR_PROVIDER=auto
VLM_BASE_URL=https://api.openai.com/v1
VLM_API_KEY=sk-...
VLM_MODEL=gpt-4o-mini

# .env — contoh Ollama lokal (llava), tetap offline
OCR_PROVIDER=auto
VLM_BASE_URL=http://localhost:11434/v1
VLM_API_KEY=ollama
VLM_MODEL=llava
```

- `tesseract`: hanya Tesseract offline (tanpa biaya/API key).
- `vlm`: hanya VLM — gagal tegas (`VLM_NOT_CONFIGURED` / `VLM_FAILED`) kalau key kosong atau request gagal.
- `auto` (default, VLM utama): coba VLM dulu, otomatis fallback ke Tesseract bila VLM belum dikonfigurasi/gagal. Response menyertakan `ocr_provider` + `fallback_used`.
- **Tanpa isi manual**: `POST /api/ocr/ktp?provider=auto&auto_confirm=1` (hanya bila diminta eksplisit; frontend baru tidak memakainya) langsung mengkonfirmasi bila **semua 13 kolom terisi + NIK 16 digit + tanggal `DD-MM-YYYY` + confidence ≥ `VLM_AUTO_CONFIRM_MIN_CONFIDENCE`**. Response `auto_confirmed=true, ktp_confirmed=true` dan frontend lompat ke `/beranda` tanpa halaman periksa. Bila tidak lengkap → tetap ke halaman periksa seperti biasa.
- Hasil yang tidak lengkap tetap draft yang wajib dikonfirmasi user di `POST /api/ocr/ktp/confirm`.
- Cek status: `GET /api/ocr/providers` (tanpa membocorkan key).

## Privacy & Data Handling

- **NIK** is stored as plain text in the database (protect the database itself — see
  "Remaining Limitations") but is **masked everywhere it's displayed**
  (`3273************`) and is **excluded from CSV/Excel exports by default**.
- **KTP photos** are never served via a public URL. By default
  (`KTP_RETENTION_DELETE_AFTER_OCR=true`) the uploaded image file is deleted from disk
  immediately after OCR runs — only the extracted text fields remain in the database.
- NIK and other sensitive values are never written to application logs or included in
  error messages (see `app/utils/privacy.py` and the global error handler in
  `app/main.py`, which never leaks stack traces to the client).
- File uploads are validated by content-type and size, written under a
  server-generated random filename (never the user-supplied filename) inside a single
  confined `UPLOAD_DIR`, preventing path traversal.

## Deployment

- Never hardcode `localhost` — the frontend reads `VITE_API_URL` and the backend reads
  `CORS_ORIGINS` / `DATABASE_URL` from the environment.
- Run the backend behind a production ASGI setup, e.g.:
  `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4` (or behind
  gunicorn+uvicorn workers / your platform's process manager).
- Put the API behind HTTPS/TLS termination (reverse proxy / load balancer) in
  production — cookies/tokens should never travel over plain HTTP outside local dev.
- Set real, unique `SECRET_KEY` / `JWT_SECRET` values and a strong `SEED_ADMIN_PASSWORD`
  before first run in any shared/production environment.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `alembic upgrade head` fails to connect | Check `DATABASE_URL` and that PostgreSQL is running/reachable |
| Frontend gets CORS errors in the browser console | Add the frontend's exact origin to `CORS_ORIGINS` in the backend `.env` |
| OCR always returns empty fields | Ensure `tesseract-ocr` and `tesseract-ocr-ind` are installed on the backend host/image |
| Admin login always fails | Confirm you ran the seed script with `SEED_ADMIN_PASSWORD` set, and that you're using that exact password |
| 401 on every admin request from the frontend | Token may have expired (`ACCESS_TOKEN_EXPIRE_MINUTES`) — log in again |
| A new/free-text jabatan gets 0 questions | Should not happen — the backend falls back to the full active question set for any position without a specific mapping. If you see this, check that at least one active question exists in `questions` |

## Remaining Limitations

Documented honestly, not hidden:

- **NIK is stored unencrypted at rest** in PostgreSQL (only masked on display/export).
  For a production deployment handling real employee data, add column-level encryption
  (e.g. `pgcrypto`) or an application-level encryption layer for the `nik` column, and
  restrict direct database access.
- **No automated data-retention/deletion job** is implemented yet — the schema and
  `KtpDocument.file_deleted` flag support building one (e.g. a scheduled job to purge
  participant PII after a configurable retention period), but the job itself is not
  included.
- **OCR accuracy** depends entirely on Tesseract's quality on a given photo; it is a
  best-effort draft by design and always requires user confirmation — do not expect
  perfect extraction on low-quality photos.
- **Rate limiting** is wired up via `slowapi` but only a global limiter instance is
  configured; per-endpoint limits (e.g. stricter limits on `/api/admin/login`) are not
  yet applied and should be added before public production exposure.
- **Result categories/questions seed data are illustrative test data only** and must
  be replaced by a psychologist-validated instrument before any real use.
- Frontend has no automated test suite (Jest/RTL/Playwright) yet — it has been
  manually verified end-to-end against the live backend and type-checked via
  `tsc -b`, but there are no automated frontend tests in this repository.
- **Chat admin** memakai polling, tanpa notifikasi suara/push. Pengunjung yang menghapus data
  peramban kehilangan akses ke percakapan lamanya (admin tetap menyimpan riwayatnya).
