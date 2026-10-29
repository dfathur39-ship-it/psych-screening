# Scan KTP dengan AI — catatan perubahan

Ekstrak zip ini DI ATAS folder project (timpa file dengan path yang sama). Tidak ada migration baru.

## Setelah ekstrak (PowerShell)
    cd D:\Projects\Go\psych-screening\backend
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt        # menambah anthropic==2.3.0
    # edit backend\.env:
    #   VLM_PROVIDER=anthropic
    #   ANTHROPIC_API_KEY=sk-ant-...
    #   VLM_AUTO_CONFIRM=false
    alembic upgrade head
    uvicorn app.main:app --reload --port 8000
    # terminal lain
    cd ..\frontend; npm run dev
    # test
    cd ..\backend; pytest tests -v

Docker: isi .env (root) lalu `docker compose up --build -d`.

## API key
https://console.anthropic.com/ -> Settings -> API Keys -> Create Key. Simpan hanya di .env.

## Cara mencoba
Buka http://localhost:5173 -> Data diri -> Profil -> Scan KTP -> unggah foto -> periksa data (✓ ⚠ ✕) -> Konfirmasi.
Swagger: http://localhost:8000/docs (POST /api/ktp/scan).
