import { useLocation } from "react-router-dom";

// Beranda, Profil, and Hubungi kami already have Bantuan in the header.
const SHOW_ON = ["/data-diri", "/profil/ktp", "/screening", "/hasil"];

/** Floating "Butuh bantuan?" link inside the screening flow. Opens in a new tab so
 *  the participant never loses the form or answers they are working on. */
export default function HelpFab() {
  const { pathname } = useLocation();
  if (!SHOW_ON.some((p) => pathname === p || pathname.startsWith(`${p}/`))) return null;
  return (
    <a className="help-fab" href="/bantuan" target="_blank" rel="noopener noreferrer">
      Butuh bantuan?
    </a>
  );
}
