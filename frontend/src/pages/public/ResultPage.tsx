import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useScreening } from "../../context/ScreeningContext";
import { getScreeningResult } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { ConfirmDialog, Spinner } from "../../components/Common";
import FlowLayout from "../../components/FlowLayout";
import type { ScreeningResult } from "../../api/types";

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
  if (!result) return <FlowLayout><Spinner label="Memuat hasil..." /></FlowLayout>;

  return (
    <FlowLayout>
      <div className="result-card">
        <span className="result-badge" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12.5l4.5 4.5L19 7.5" />
          </svg>
        </span>
        <h1 className="flow-title">Terima kasih, skrining selesai</h1>
        <div className="result-score">{score}</div>
        <div className="result-category">{result.category_name}</div>
        {result.message && <p className="result-message">{result.message}</p>}
        {result.recommendation && (
          <div className="result-reco">
            <strong>Saran untuk Anda</strong>
            <p>{result.recommendation}</p>
          </div>
        )}
        <p className="disclaimer">{result.disclaimer}</p>

        <div className="btn-row result-actions">
          <button className="btn btn-primary btn-lg" onClick={() => void handleDone()}>Selesai</button>
          <button className="btn btn-secondary btn-lg" onClick={() => setConfirmLogout(true)}>Keluar</button>
        </div>
        <p className="form-hint">Sudah selesai mengerjakan? Anda bisa keluar dari perangkat ini sekarang.</p>
      </div>

      <ConfirmDialog
        open={confirmLogout}
        title="Keluar"
        message="Hasil skrining Anda sudah tersimpan di server. Anda akan keluar dari perangkat ini dan perlu mengisi data diri yang sama untuk masuk lagi nanti. Lanjutkan?"
        onConfirm={handleLogout}
        onCancel={() => setConfirmLogout(false)}
      />
    </FlowLayout>
  );
}
