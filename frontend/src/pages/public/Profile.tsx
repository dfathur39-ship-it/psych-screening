import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useProfile, useScreening } from "../../context/ScreeningContext";
import { ConfirmDialog } from "../../components/Common";
import { ReadScene } from "../../components/Illustrations";

export default function Profile() {
  const profile = useProfile();
  const { refreshProfile, reset } = useScreening();
  const [confirmOut, setConfirmOut] = useState(false);

  useEffect(() => { void refreshProfile(); }, [refreshProfile]);

  const ktpOk = profile.ktp_confirmed;
  const rows: [string, string][] = [
    ["Nama", profile.nama],
    ["Email", profile.email ?? "-"],
    ["Nomor HP", profile.no_hp],
    ["Usia", `${profile.usia} tahun`],
    ["Jabatan", profile.jabatan],
  ];

  return (
    <main className="page-narrow">
      <div className="page-head">
        <div>
          <h1>Profil</h1>
          <p className="page-lead">Data dirimu dan konfirmasi KTP. KTP perlu dikonfirmasi dulu sebelum kamu mulai menjawab pertanyaan.</p>
        </div>
        <div className="spot" aria-hidden="true"><ReadScene /></div>
      </div>

      <section className="card pf-card">
        <h2>Data diri</h2>
        <dl className="pf-list">
          {rows.map(([k, v]) => (
            <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
          ))}
        </dl>
      </section>

      <section className="card pf-card" id="ktp">
        <div className="pf-head">
          <h2>Konfirmasi KTP</h2>
          <span className={`badge ${ktpOk ? "badge-success" : "badge-warning"}`}>
            {ktpOk ? "Sudah dikonfirmasi" : "Belum dikonfirmasi"}
          </span>
        </div>
        <p className="pf-text">
          {ktpOk
            ? "Terima kasih, KTP‑mu sudah dikonfirmasi. Foto ulang hanya perlu kalau ada data yang salah, dan datanya perlu kamu konfirmasi lagi."
            : "Foto KTP‑mu, kami bantu membaca datanya, lalu kamu periksa dan koreksi."}
        </p>
        {ktpOk && profile.nik_masked && (
          <dl className="pf-list">
            <div><dt>NIK</dt><dd className="nik-mask">{profile.nik_masked}</dd></div>
          </dl>
        )}
        <div className="pf-actions">
          <Link className={`btn ${ktpOk ? "btn-secondary" : "btn-primary"}`} to="/profil/ktp">
            {ktpOk ? "Foto ulang KTP" : "Pindai KTP"}
          </Link>
          {ktpOk && <Link className="btn btn-primary" to="/beranda">Ke beranda</Link>}
        </div>
      </section>

      <p className="pf-switch">
        Bukan kamu? <button className="link-btn" onClick={() => setConfirmOut(true)}>Gunakan data diri lain</button>
      </p>

      <ConfirmDialog
        open={confirmOut}
        title="Gunakan data diri lain"
        message="Kamu akan keluar dari data diri ini di perangkat ini dan perlu mengisi data diri lagi. Percakapan dan skrining yang sedang berjalan tidak bisa dibuka lagi dari sini. Lanjutkan?"
        onConfirm={() => { setConfirmOut(false); reset(); /* MemberLayout then sends them to fill in data diri */ }}
        onCancel={() => setConfirmOut(false)}
      />
    </main>
  );
}
