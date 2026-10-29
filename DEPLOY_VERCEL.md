# Deploy: Supabase + Vercel

Database: Supabase (tabel dan data awal sudah terpasang).
Backend : Vercel project `psych-screening-api` (root directory `backend`).
Frontend: Vercel project `psych-screening-web` (root directory `frontend`).

1. Push seluruh folder ini ke satu repo GitHub (privat disarankan). File .env tidak ikut ter-push.
2. Vercel > psych-screening-api > Settings > Git > Connect repository. Pastikan Root Directory = `backend`.
3. Vercel > psych-screening-api > Settings > Environment Variables, tambahkan `DATABASE_URL`
   (tipe Sensitive) dengan connection string Supabase pooler:
   postgresql+psycopg2://postgres.<project-ref>:<PASSWORD>@<host-pooler>:6543/postgres
   (Supabase > Connect > Transaction pooler; tambahkan `+psycopg2` setelah `postgresql`).
4. Ulangi langkah 2 untuk psych-screening-web (Root Directory = `frontend`).
5. Redeploy kedua project.
