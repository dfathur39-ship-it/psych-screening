import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useScreening } from "../context/ScreeningContext";
import { ConfirmDialog } from "./Common";

export const HEART =
  "M12 21s-7-4.4-9.3-9C1.2 8.8 3.3 5 7 5c2 0 3.4 1 5 3 1.6-2 3-3 5-3 3.7 0 5.8 3.8 4.3 7-2.3 4.6-9.3 9-9.3 9z";

export function BrandMark() {
  return (
    <span className="lp-logo">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M5 19c0-8.500 5-14 14.500-14.500C19 14 13.500 19.500 5 19zM5 19c2.500-4.500 5.500-7.500 9-9.500" />
      </svg>
    </span>
  );
}

const cls = ({ isActive }: { isActive: boolean }) => (isActive ? "active" : "");

/** Site header. Once the visitor has filled in their data diri it also links to Beranda and Profil. */
export default function PublicHeader() {
  const { participantId, sessionId, reset } = useScreening();
  const navigate = useNavigate();
  const [confirmOut, setConfirmOut] = useState(false);
  const signedIn = participantId !== null;

  const handleLogout = () => {
    setConfirmOut(false);
    reset();
    navigate("/");
  };

  return (
    <nav className="lp-nav">
      <Link to={signedIn ? "/beranda" : "/"} className="lp-brand">
        <BrandMark />
        <span>Skrining <em>Psikologi</em></span>
      </Link>
      <div className="lp-links">
        {signedIn && <NavLink to="/beranda" className={cls}>Beranda</NavLink>}
        {signedIn && <NavLink to="/profil" className={cls}>Profil</NavLink>}
        <NavLink to="/bantuan" className={cls}>Bantuan</NavLink>
        <NavLink to="/kontak" className={cls}>Hubungi kami</NavLink>
      </div>
      <div className="lp-nav-cta">
        {signedIn ? (
          <button className="btn btn-secondary btn-sm" onClick={() => setConfirmOut(true)}>Keluar</button>
        ) : (
          <Link to="/data-diri" className="btn btn-primary btn-sm">Mulai</Link>
        )}
      </div>

      <ConfirmDialog
        open={confirmOut}
        title="Keluar"
        message={
          sessionId
            ? "Kamu masih mengerjakan skrining. Keluar sekarang berarti kamu perlu mengisi data diri lagi untuk melanjutkan di perangkat ini. Jawaban yang sudah tersimpan tetap aman di server. Lanjutkan keluar?"
            : "Kamu akan keluar dari perangkat ini. Untuk masuk lagi, isi data diri yang sama (nama, email, dan nomor HP)."
        }
        onConfirm={handleLogout}
        onCancel={() => setConfirmOut(false)}
      />
    </nav>
  );
}
