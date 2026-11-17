import { useCallback, useEffect, useRef, useState } from "react";

interface Props {
  /** Dipanggil dengan foto hasil jepretan. */
  onCapture: (file: File) => void;
  /** Dipanggil saat pengguna menutup kamera atau memilih cara lain. */
  onClose: () => void;
  /** Dipanggil saat kamera tidak bisa dipakai dan pengguna memilih unggah dari perangkat. */
  onFallback: () => void;
}

const MAX_SIDE = 1800; // sisi terpanjang hasil foto; menjaga ukuran file di bawah batas unggah

function cameraErrorMessage(err: unknown): string {
  const name = err instanceof DOMException ? err.name : "";
  if (name === "NotAllowedError" || name === "SecurityError") {
    return "Izin kamera belum diberikan. Izinkan kamera lewat ikon gembok di kolom alamat browser, lalu coba lagi.";
  }
  if (name === "NotFoundError" || name === "OverconstrainedError") return "Kamera tidak ditemukan di perangkat ini.";
  if (name === "NotReadableError" || name === "AbortError") return "Kamera sedang dipakai aplikasi lain. Tutup aplikasi itu, lalu coba lagi.";
  return "Kamera belum bisa dibuka.";
}

export default function CameraCapture({ onCapture, onClose, onFallback }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [facing, setFacing] = useState<"environment" | "user">("environment");
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMultiple, setHasMultiple] = useState(false);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => {
    let cancelled = false;
    setReady(false);
    setError(null);
    (async () => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setError("Browser ini belum mendukung kamera langsung.");
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: facing }, width: { ideal: 1920 }, height: { ideal: 1080 } },
          audio: false,
        });
        if (cancelled) { stream.getTracks().forEach((t) => t.stop()); return; }
        stop();
        streamRef.current = stream;
        const v = videoRef.current;
        if (v) {
          v.srcObject = stream;
          await v.play().catch(() => undefined);
        }
        setReady(true);
        const devices = await navigator.mediaDevices.enumerateDevices().catch(() => []);
        if (!cancelled) setHasMultiple(devices.filter((d) => d.kind === "videoinput").length > 1);
      } catch (err) {
        if (!cancelled) setError(cameraErrorMessage(err));
      }
    })();
    return () => { cancelled = true; stop(); };
  }, [facing, stop]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const snap = () => {
    const v = videoRef.current;
    if (!v || !v.videoWidth) return;
    const scale = Math.min(1, MAX_SIDE / Math.max(v.videoWidth, v.videoHeight));
    const w = Math.round(v.videoWidth * scale);
    const h = Math.round(v.videoHeight * scale);
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    canvas.getContext("2d")?.drawImage(v, 0, 0, w, h);
    canvas.toBlob(
      (blob) => {
        if (!blob) { setError("Foto belum berhasil diambil. Coba sekali lagi."); return; }
        stop();
        onCapture(new File([blob], `ktp-${Date.now()}.jpg`, { type: "image/jpeg" }));
      },
      "image/jpeg",
      0.9,
    );
  };

  return (
    <div className="cam" role="dialog" aria-label="Ambil foto KTP">
      {error ? (
        <div className="cam-error">
          <p>{error}</p>
          <div className="btn-row">
            <button className="btn btn-secondary" onClick={onClose}>Kembali</button>
            <button className="btn btn-primary" onClick={onFallback}>Pilih foto dari perangkat</button>
          </div>
        </div>
      ) : (
        <>
          <div className="cam-view">
            <video ref={videoRef} playsInline muted autoPlay />
            <div className="cam-guide" aria-hidden="true"><span /><span /><span /><span /></div>
            {!ready && <div className="cam-wait">Membuka kamera...</div>}
          </div>
          <p className="form-hint cam-hint">Pas-kan KTP di dalam bingkai, pastikan semua sisinya terlihat dan tidak silau.</p>
          <div className="cam-actions">
            <button className="btn btn-secondary" onClick={onClose}>Batal</button>
            <button className="btn btn-primary btn-lg cam-shutter" onClick={snap} disabled={!ready}>Ambil foto</button>
            {hasMultiple && (
              <button className="btn btn-secondary" onClick={() => setFacing((f) => (f === "environment" ? "user" : "environment"))} disabled={!ready}>
                Putar kamera
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
