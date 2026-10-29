import { useEffect, useRef, useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useScreening } from "../../context/ScreeningContext";
import { scanKtp } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { useToast } from "../../components/Common";
import FlowLayout from "../../components/FlowLayout";

const MAX_SIZE_MB = 4; // batas body fungsi Vercel 4,5 MB
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/jpg"];
const TIPS = ["Letakkan KTP rata di permukaan gelap", "Cahaya cukup, tanpa pantulan", "Seluruh kartu terlihat jelas"];

export default function KtpScan() {
  const { participantId } = useScreening();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  // free the object URL when the preview changes or the page closes
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  if (!participantId) return <Navigate to="/data-diri" replace />;

  const handleFile = (f: File | null | undefined) => {
    if (!f) return;
    if (!ALLOWED_TYPES.includes(f.type)) {
      showToast("Format file harus JPG, PNG, atau WEBP", "error");
      return;
    }
    if (f.size > MAX_SIZE_MB * 1024 * 1024) {
      showToast(`Ukuran file maksimal ${MAX_SIZE_MB}MB`, "error");
      return;
    }
    setError(null);
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  // Isi manual selalu tersedia: user tidak wajib memakai scan AI.
  const goManual = () => navigate("/profil/ktp/konfirmasi", { state: { manual: true } });

  const handleProcess = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      // Hasil scan hanya draft: TIDAK disimpan. User memeriksa dulu di halaman berikutnya.
      const scan = await scanKtp(participantId, file);
      showToast("Data KTP berhasil dibaca. Silakan periksa kembali.", "success");
      navigate("/profil/ktp/konfirmasi", { state: { scan } });
    } catch (err) {
      // AI gagal bukan jalan buntu: user bisa scan ulang atau isi manual.
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <FlowLayout embedded step={1}>
      <Link className="back-link" to="/profil">&larr; Kembali ke profil</Link>
      <h1 className="flow-title">Scan KTP dengan AI</h1>
      <p className="flow-sub">AI membantu mengisi data dari foto KTP. Hasilnya hanya draft: Anda memeriksa dan memperbaikinya di langkah berikutnya sebelum disimpan. Tidak mau scan? Anda bisa mengisi manual.</p>

      {preview ? (
        <div className={`ktp-preview ${loading ? "scanning" : ""}`}>
          <img src={preview} alt="Pratinjau KTP" />
          {loading && <span className="scan-line" />}
        </div>
      ) : (
        <div
          className={`id-frame ${dragging ? "dragging" : ""}`}
          role="button" tabIndex={0}
          onClick={() => fileInputRef.current?.click()}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click(); }}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files?.[0]); }}
        >
          <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <rect x="3" y="5" width="18" height="14" rx="2.5" /><circle cx="8.5" cy="11" r="2" /><path d="M13.5 10h4M13.5 13.5h3M6 16c.6-1.3 1.6-2 2.500-2s1.900.7 2.500 2" />
          </svg>
          <span className="c1" /><span className="c2" />
          <p><strong>Tarik foto KTP ke sini</strong> atau klik untuk memilih</p>
          <p className="form-hint">JPG, PNG, atau WEBP. Maksimal {MAX_SIZE_MB}MB.</p>
        </div>
      )}

      <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/webp" hidden
        onChange={(e) => { handleFile(e.target.files?.[0]); e.target.value = ""; }} />
      <input ref={cameraInputRef} type="file" accept="image/*" capture="environment" hidden
        onChange={(e) => { handleFile(e.target.files?.[0]); e.target.value = ""; }} />

      <div className="btn-row">
        <button className="btn btn-secondary" disabled={loading} onClick={() => cameraInputRef.current?.click()}>
          Gunakan kamera
        </button>
        <button className="btn btn-secondary" disabled={loading} onClick={() => fileInputRef.current?.click()}>
          {preview ? "Ganti foto" : "Pilih dari galeri"}
        </button>
      </div>

      {loading && <div className="notice" role="status">Memproses KTP...</div>}
      {error && (
        <div className="notice notice-danger" role="alert">
          {error}
          <div className="form-hint">Anda bisa scan ulang, mengganti foto, atau mengisi data secara manual.</div>
        </div>
      )}

      <button className="btn btn-primary btn-block btn-lg" disabled={!file || loading} onClick={handleProcess}>
        {loading ? "Memproses KTP..." : error ? "Scan Ulang" : "Scan dengan AI"}
      </button>
      <button className="btn btn-secondary btn-block" style={{ marginTop: 10 }} disabled={loading} onClick={goManual}>
        Isi Manual
      </button>

      <ul className="tips">
        {TIPS.map((t) => <li key={t}>{t}</li>)}
      </ul>
    </FlowLayout>
  );
}
