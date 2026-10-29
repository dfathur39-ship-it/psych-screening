import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useScreening } from "../../context/ScreeningContext";
import PublicHeader from "../../components/PublicHeader";

const HEART =
  "M12 21s-7-4.4-9.3-9C1.2 8.8 3.3 5 7 5c2 0 3.4 1 5 3 1.6-2 3-3 5-3 3.7 0 5.8 3.8 4.3 7-2.3 4.6-9.3 9-9.3 9z";

const STEPS = [
  { title: "Isi data diri", desc: "Nama, email, usia, jabatan, dan nomor HP. Jabatan boleh diketik bebas." },
  { title: "Konfirmasi KTP di profil", desc: "Foto KTP, kami bantu membaca datanya. Anda tinggal memeriksa dan mengoreksi." },
  { title: "Jawab pertanyaan", desc: "Pilih satu dari empat jawaban. Tidak ada jawaban benar atau salah." },
  { title: "Lihat hasil", desc: "Skor dan saran langsung muncul begitu Anda selesai." },
];

const TRUST = [
  {
    title: "Data Anda terlindungi",
    desc: "NIK disamarkan di semua tampilan admin dan tidak ikut diekspor. Foto KTP dihapus setelah dibaca.",
    d: "M12 3l8 3v6c0 4.5-3.2 8.3-8 9-4.8-.7-8-4.5-8-9V6l8-3z",
  },
  {
    title: "Bukan diagnosis",
    desc: "Ini skrining awal untuk membantu Anda mengenali kondisi, bukan pengganti psikolog atau dokter.",
    d: HEART,
  },
  {
    title: "Sekitar 10 menit",
    desc: "Jumlah pertanyaan menyesuaikan jabatan. Jawaban tersimpan otomatis, aman kalau halaman ter-refresh.",
    d: "M12 7v5l3 2M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  },
];

function Arrow() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M7 17L17 7M8 7h9v9" />
    </svg>
  );
}

function Icon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  );
}

export default function Landing() {
  const navigate = useNavigate();
  const { reset, participantId, profile } = useScreening();
  const [inhale, setInhale] = useState(true);

  // Keeps the label in step with the 8s breathing animation (4s in, 4s out).
  useEffect(() => {
    const t = setInterval(() => setInhale((v) => !v), 4000);
    return () => clearInterval(t);
  }, []);

  const handleStart = () => {
    reset(); // a new visitor always begins by filling in data diri
    navigate("/data-diri");
  };

  return (
    <div className="lp">
      <PublicHeader />

      <header className="lp-hero">
        <div className="lp-copy">
          <h1>Seberapa berat pekerjaan terasa akhir-akhir ini?</h1>
          <p>
            Jawab beberapa pertanyaan singkat untuk melihat bagaimana kondisi psikologis Anda
            terkait pekerjaan. Hasilnya langsung Anda terima, lengkap dengan saran yang bisa dilakukan.
          </p>
          <div className="lp-cta">
            {participantId ? (
              <>
                <button className="btn btn-primary btn-lg" onClick={() => navigate("/beranda")}>
                  Lanjut ke beranda <Arrow />
                </button>
                <button className="btn btn-secondary btn-lg" onClick={handleStart}>Gunakan data diri lain</button>
              </>
            ) : (
              <>
                <button className="btn btn-primary btn-lg" onClick={handleStart}>
                  Mulai skrining <Arrow />
                </button>
                <a className="btn btn-secondary btn-lg" href="#langkah">Lihat langkahnya</a>
              </>
            )}
          </div>
          <p className="lp-note">
            {participantId && profile ? `Masuk sebagai ${profile.nama}.` : "Cukup isi data diri, tanpa kata sandi."}
          </p>
        </div>
        <div className="breath" aria-hidden="true">
          <span className="breath-ring r1" />
          <span className="breath-ring r2" />
          <div className="breath-core">
            <span className="breath-label" key={String(inhale)}>{inhale ? "Tarik napas" : "Hembuskan"}</span>
          </div>
          <p className="breath-caption">Ambil napas sejenak. Tidak perlu buru-buru.</p>
        </div>
      </header>

      <section className="lp-section" id="langkah">
        <h2>Empat langkah sampai hasil</h2>
        <ol className="steps">
          {STEPS.map((s, i) => (
            <li className="step" key={s.title}>
              <div className="step-num">{i + 1}</div>
              <h3>{s.title}</h3>
              <p>{s.desc}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="trust">
        {TRUST.map((t) => (
          <div className="trust-item" key={t.title}>
            <span className="trust-icon">
              <Icon d={t.d} />
            </span>
            <div>
              <h3>{t.title}</h3>
              <p>{t.desc}</p>
            </div>
          </div>
        ))}
      </section>

      <footer className="lp-foot">Hasil skrining ini bukan diagnosis psikologis atau diagnosis medis.</footer>
    </div>
  );
}
