import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useProfile, useScreening } from "../../context/ScreeningContext";
import { requestRetake, startScreening } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { useToast } from "../../components/Common";
import { WaveScene } from "../../components/Illustrations";

function Tick() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12.5l4.5 4.5L19 7.5" />
    </svg>
  );
}

function Lock() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 018 0v3" />
    </svg>
  );
}

/** Home for a participant. Questions stay locked until the KTP has been confirmed in Profil,
 *  and once a screening is completed, a redo needs the participant to ask and an admin to approve it. */
export default function Dashboard() {
  const profile = useProfile();
  const { setSessionId, refreshProfile } = useScreening();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [starting, setStarting] = useState(false);
  const [reason, setReason] = useState("");
  const [requesting, setRequesting] = useState(false);

  // Statuses can be stale after finishing a screening or confirming a KTP, so re-read them on arrival.
  useEffect(() => { void refreshProfile(); }, [refreshProfile]);

  const ktpOk = profile.ktp_confirmed;
  const resuming = profile.in_progress_session_id !== null;
  const alreadyDone = profile.completed_session_id !== null && !resuming;
  const retakeStatus = profile.retake_status;
  const canStart = ktpOk && (!alreadyDone || retakeStatus === "approved");
  const firstName = profile.nama.trim().split(/\s+/)[0];

  const handleStart = async () => {
    setStarting(true);
    try {
      const session = await startScreening(profile.id, profile.jabatan);
      setSessionId(session.session_id);
      navigate("/screening");
    } catch (err) {
      showToast(getErrorMessage(err), "error");
      void refreshProfile(); // e.g. the KTP needs re-confirming, or the retake approval was already used elsewhere
      setStarting(false);
    }
  };

  const handleViewResult = () => {
    setSessionId(profile.completed_session_id);
    navigate("/hasil");
  };

  const handleRequestRetake = async () => {
    setRequesting(true);
    try {
      await requestRetake(profile.id, reason.trim() || undefined);
      setReason("");
      showToast("Permintaan sudah terkirim. Tunggu persetujuan admin ya.", "success");
      void refreshProfile();
    } catch (err) {
      showToast(getErrorMessage(err), "error");
    } finally {
      setRequesting(false);
    }
  };

  const questionStepLabel = () => {
    if (!ktpOk) return "Terbuka setelah KTP‑mu dikonfirmasi di profil.";
    if (resuming) return "Kamu masih punya skrining yang belum selesai. Jawabanmu sebelumnya sudah tersimpan.";
    if (!alreadyDone) return "Sekitar 10 menit. Tidak ada jawaban benar atau salah.";
    if (retakeStatus === "approved") return "Admin sudah menyetujui permintaanmu. Kamu bisa mulai sekarang.";
    return "Skriningmu sudah selesai dan tidak bisa diulang tanpa persetujuan admin.";
  };

  return (
    <main className="page-narrow">
      <div className="page-head">
        <div>
          <h1>Halo, {firstName}</h1>
          <p className="page-lead">
            {!ktpOk
              ? "Sebelum mulai menjawab, konfirmasi KTP‑mu dulu di halaman Profil."
              : canStart
                ? "Semua sudah siap. Mulai kapan pun kamu merasa nyaman."
                : "Skriningmu sudah selesai. Ajukan permintaan di bawah kalau mau mengulang."}
          </p>
        </div>
        <div className="spot" aria-hidden="true"><WaveScene /></div>
      </div>

      <ol className="hm-steps">
        <li className="hm-step done">
          <span className="hm-mark"><Tick /></span>
          <div className="hm-body">
            <h2>Data diri</h2>
            <p>Nama, email, nomor HP, dan jabatan sudah tersimpan.</p>
          </div>
          <Link className="link-btn" to="/profil">Lihat</Link>
        </li>

        <li className={`hm-step ${ktpOk ? "done" : "current"}`}>
          <span className="hm-mark">{ktpOk ? <Tick /> : 2}</span>
          <div className="hm-body">
            <h2>Konfirmasi KTP</h2>
            <p>{ktpOk ? "KTP‑mu sudah diperiksa dan dikonfirmasi." : "Unggah foto KTP, lalu periksa dan koreksi hasil bacaannya."}</p>
            {!ktpOk && <Link className="btn btn-primary btn-sm hm-action" to="/profil">Konfirmasi KTP</Link>}
          </div>
          {ktpOk && <Link className="link-btn" to="/profil">Lihat</Link>}
        </li>

        <li className={`hm-step ${canStart ? "current" : ktpOk ? "done" : "locked"}`} aria-disabled={!ktpOk}>
          <span className="hm-mark">{!ktpOk ? <Lock /> : alreadyDone && !canStart ? <Tick /> : 3}</span>
          <div className="hm-body">
            <h2>Jawab pertanyaan</h2>
            <p>{questionStepLabel()}</p>
            {canStart && (
              <button className="btn btn-primary btn-sm hm-action" disabled={starting} onClick={handleStart}>
                {starting ? "Sebentar ya..." : resuming ? "Lanjutkan skrining" : "Mulai skrining"}
              </button>
            )}
          </div>
        </li>
      </ol>

      {profile.completed_session_id && (
        <div className="card hm-last">
          <div>
            <h3>Hasil skrining sebelumnya</h3>
            <p>Kamu pernah menyelesaikan skrining. Hasilnya masih bisa dibuka.</p>
          </div>
          <button className="btn btn-secondary" onClick={handleViewResult}>Lihat hasil</button>
        </div>
      )}

      {alreadyDone && (
        <section className="card retake-card">
          <h3>Mengulang skrining</h3>
          {retakeStatus === "pending" && (
            <p className="notice">Permintaanmu sedang menunggu persetujuan admin.</p>
          )}
          {retakeStatus === "approved" && (
            <p className="notice notice-success">Permintaanmu disetujui. Tekan "Mulai skrining" di atas.</p>
          )}
          {retakeStatus === "rejected" && (
            <p className="notice notice-danger">
              Permintaan sebelumnya belum disetujui admin. Kamu bisa mengajukan lagi di bawah ini.
            </p>
          )}
          {retakeStatus !== "pending" && retakeStatus !== "approved" && (
            <>
              <p className="pf-text">
                Skriningmu sudah selesai. Untuk mengulang, kirim permintaan berikut dan tunggu admin menyetujuinya.
              </p>
              <div className="form-group">
                <label htmlFor="retake-reason">Alasan (opsional)</label>
                <textarea id="retake-reason" className="form-control" rows={2} maxLength={500}
                  value={reason} onChange={(e) => setReason(e.target.value)}
                  placeholder="Contoh: Ada gangguan saat pertama kali mengerjakan" />
              </div>
              <button className="btn btn-secondary" disabled={requesting} onClick={() => void handleRequestRetake()}>
                {requesting ? "Sebentar ya..." : "Ajukan mengulang skrining"}
              </button>
            </>
          )}
        </section>
      )}
    </main>
  );
}
