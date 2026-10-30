import { useNavigate } from "react-router-dom";
import { useScreening } from "../../context/ScreeningContext";
import PublicHeader from "../../components/PublicHeader";
import { HeroScene, ThinkScene, FormScene, RestScene, Trio } from "../../components/Illustrations";

const STEPS = [
  {
    title: "Kenalan dulu",
    desc: "Isi nama, email, usia, jabatan, dan nomor HP. Foto KTP boleh kamu unggah supaya datanya terisi otomatis, lalu tinggal diperiksa.",
    Art: ThinkScene,
  },
  {
    title: "Jawab dengan tenang",
    desc: "Pilih satu dari empat jawaban untuk tiap pertanyaan. Tidak ada jawaban benar atau salah, dan jawabanmu tersimpan otomatis.",
    Art: FormScene,
  },
  {
    title: "Lihat hasilnya",
    desc: "Begitu selesai, kamu langsung mendapat gambaran kondisimu beserta saran kecil yang bisa dicoba hari ini.",
    Art: RestScene,
  },
];

const FACTS = [
  { title: "Datamu terjaga", desc: "NIK disamarkan di tampilan admin dan tidak ikut diekspor. Foto KTP dihapus setelah dibaca.", d: "M12 3l8 3v6c0 4.5-3.2 8.3-8 9-4.8-.7-8-4.5-8-9V6l8-3z" },
  { title: "Sekitar 10 menit", desc: "Jumlah pertanyaan menyesuaikan jabatanmu. Kalau halaman ter-refresh, jawabanmu tidak hilang.", d: "M12 7v5l3 2M21 12a9 9 0 11-18 0 9 9 0 0118 0z" },
  { title: "Bukan diagnosis", desc: "Ini gambaran awal untuk mengenali dirimu sendiri. Bukan pengganti psikolog atau dokter.", d: "M12 21s-7-4.4-9.3-9C1.2 8.8 3.3 5 7 5c2 0 3.4 1 5 3 1.6-2 3-3 5-3 3.7 0 5.8 3.8 4.3 7-2.3 4.6-9.3 9-9.3 9z" },
];

function Arrow() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

function Icon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={d} />
    </svg>
  );
}

export default function Landing() {
  const navigate = useNavigate();
  const { reset, participantId, profile } = useScreening();

  const handleStart = () => {
    reset(); // pengunjung baru selalu mulai dari data diri
    navigate("/data-diri");
  };

  return (
    <div className="lp">
      <PublicHeader />

      <header className="lp-hero">
        <div className="lp-copy">
          <h1>Kenali Kondisimu, Luangkan Waktu untuk Dirimu.</h1>
          <p>Yuk, luangkan beberapa menit untuk memahami bagaimana kondisi dan perasaanmu akhir-akhir ini.</p>
          <div className="lp-cta">
            {participantId ? (
              <>
                <button className="btn btn-primary btn-lg" onClick={() => navigate("/beranda")}>
                  Lanjutkan <Arrow />
                </button>
                <button className="btn btn-secondary btn-lg" onClick={handleStart}>Pakai data diri lain</button>
              </>
            ) : (
              <>
                <button className="btn btn-primary btn-lg" onClick={handleStart}>
                  Mulai Skrining <Arrow />
                </button>
                <a className="btn btn-secondary btn-lg" href="#langkah">Lihat caranya</a>
              </>
            )}
          </div>
          <p className="lp-note">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10" /></svg>
            {participantId && profile ? `Halo, ${profile.nama}. Senang kamu kembali.` : "Tanpa kata sandi. Cukup isi data dirimu."}
          </p>
        </div>
        <div className="hero-art">
          <HeroScene />
          <span className="hero-tag t1">Tidak ada jawaban salah</span>
          <span className="hero-tag t2">Pelan-pelan saja</span>
        </div>
      </header>

      <section className="lp-facts" aria-label="Hal yang perlu kamu tahu">
        {FACTS.map((f) => (
          <div className="fact" key={f.title}>
            <span className="fact-icon"><Icon d={f.d} /></span>
            <div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          </div>
        ))}
      </section>

      <section className="lp-section" id="langkah">
        <h2>Tiga langkah, tanpa ribet</h2>
        <p className="section-lead">Kamu bisa berhenti kapan saja dan melanjutkannya nanti dari perangkat yang sama.</p>
        <ol className="steps">
          {STEPS.map((s, i) => (
            <li className="step" key={s.title}>
              <div className="step-art"><s.Art /></div>
              <span className="step-num">{i + 1}</span>
              <h3>{s.title}</h3>
              <p>{s.desc}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="lp-band">
        <div className="lp-band-in">
          <div>
            <h2>Kamu tidak sendirian menghadapinya.</h2>
            <p>Banyak orang merasakan lelah yang sama. Mengenalinya adalah langkah pertama, dan kamu sudah selangkah lebih dekat.</p>
            <button className="btn btn-primary btn-lg" onClick={participantId ? () => navigate("/beranda") : handleStart}>
              {participantId ? "Lanjutkan" : "Mulai Skrining"} <Arrow />
            </button>
          </div>
          <div className="lp-band-art"><Trio /></div>
        </div>
      </section>

      <footer className="lp-foot">Hasil skrining ini bukan diagnosis psikologis atau diagnosis medis.</footer>
    </div>
  );
}
