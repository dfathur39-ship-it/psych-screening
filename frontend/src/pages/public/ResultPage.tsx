import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useScreening } from "../../context/ScreeningContext";
import { getScreeningResult } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { ConfirmDialog, Spinner } from "../../components/Common";
import FlowLayout from "../../components/FlowLayout";
import type { ScreeningResult } from "../../api/types";
import { HappyScene } from "../../components/Illustrations";

/** Counts up to `target` so the score lands with a little motion (skipped for reduced-motion users). */
function useCountUp(target: number, ms = 900) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) { setValue(target); return; }
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min((now - start) / ms, 1);
      setValue(Math.round(target * (1 - Math.pow(1 - t, 3))));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return value;
}

export default function ResultPage() {
  const { sessionId, setSessionId, refreshProfile, reset } = useScreening();
  const navigate = useNavigate();
  const [result, setResult] = useState<ScreeningResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmLogout, setConfirmLogout] = useState(false);
  const score = useCountUp(result?.total_score ?? 0);

  useEffect(() => {
    if (!sessionId) return;
    getScreeningResult(sessionId).then(setResult).catch((err) => setError(getErrorMessage(err)));
  }, [sessionId]);

  if (!sessionId) return <Navigate to="/beranda" replace />;

  const handleDone = async () => {
    setSessionId(null);
    await refreshProfile(); // so Beranda shows the finished screening, not the in-progress one
    navigate("/beranda");
  };

  const handleLogout = () => {
    setConfirmLogout(false);
    reset();
    navigate("/");
  };

  if (error) return <FlowLayout><div className="empty-state"><p>{error}</p></div></FlowLayout>;
  if (!result) return <FlowLayout><Spinner label="Menyiapkan hasilmu..." /></FlowLayout>;

  return (
    <FlowLayout>
      <div className="result-card">
        <div className="result-art" aria-hidden="true"><HappyScene /></div>
        <h1 className="flow-title">Terima kasih sudah meluangkan waktu untuk mengisi skrining ini.</h1>
        <p className="page-sub">Skor kamu</p>
        <div className="result-score">{score}</div>
        <div className="result-category">{result.category_name}</div>
        {result.message && <p className="result-message">{result.message}</p>}
        {result.recommendation && (
          <div className="result-reco">
            <strong>Saran untukmu</strong>
            <p>{result.recommendation}</p>
          </div>
        )}
        <p className="disclaimer">{result.disclaimer}</p>

        <div className="btn-row result-actions">
          <button className="btn btn-primary btn-lg" onClick={() => void handleDone()}>Selesai</button>
          <button className="btn btn-secondary btn-lg" onClick={() => setConfirmLogout(true)}>Keluar</button>
        </div>
        <p className="form-hint">Sudah selesai? Kamu boleh keluar dari perangkat ini sekarang.</p>
      </div>

      <ConfirmDialog
        open={confirmLogout}
        title="Keluar"
        message="Hasil skriningmu sudah tersimpan. Kalau keluar, kamu perlu mengisi data diri yang sama untuk masuk lagi nanti. Lanjutkan?"
        onConfirm={handleLogout}
        onCancel={() => setConfirmLogout(false)}
      />
    </FlowLayout>
  );
}
