import { useCallback, useEffect, useState } from "react";
import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import { useAdminAuth } from "../context/AdminAuthContext";
import { adminLogout, getSupportUnread, getRetakePendingCount } from "../api/services";
import { usePolling } from "../hooks/usePolling";
import { BrandMark } from "../components/PublicHeader";

const MENU = [
  { to: "/admin/dashboard", label: "Ringkasan" },
  { to: "/admin/participants", label: "Peserta" },
  { to: "/admin/screenings", label: "Skrining" },
  { to: "/admin/support", label: "Pesan", badge: "support" },
  { to: "/admin/retake-requests", label: "Ulang Skrining", badge: "retake" },
  { to: "/admin/positions", label: "Jabatan" },
  { to: "/admin/questions", label: "Pertanyaan" },
  { to: "/admin/categories", label: "Kategori Hasil" },
  { to: "/admin/audit-logs", label: "Riwayat Aktivitas" },
  { to: "/admin/export", label: "Ekspor Data" },
  { to: "/admin/profil", label: "Profil Saya" },
];

export function RequireAdminAuth() {
  const { token } = useAdminAuth();
  if (!token) return <Navigate to="/admin/login" replace />;
  return <Outlet />;
}

export default function AdminLayout() {
  const { username, role, logout } = useAdminAuth();
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);
  const [pendingRetake, setPendingRetake] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setMenuOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  const refreshUnread = useCallback(async () => {
    try {
      setUnread((await getSupportUnread()).unread_messages);
    } catch {
      // badge is best-effort; ignore transient errors
    }
  }, []);
  usePolling(refreshUnread, 10000);

  const refreshRetakeCount = useCallback(async () => {
    try {
      setPendingRetake((await getRetakePendingCount()).pending);
    } catch {
      // badge is best-effort; ignore transient errors
    }
  }, []);
  usePolling(refreshRetakeCount, 10000);

  const handleLogout = async () => {
    try {
      await adminLogout();
    } catch {
      // ignore network errors on logout; clear client state regardless
    }
    logout();
    navigate("/admin/login");
  };

  return (
    <div className="admin-shell">
      <aside className={`admin-sidebar${menuOpen ? " open" : ""}`} id="admin-menu">
        <div className="lp-brand"><BrandMark />Ruang <em>Admin</em></div>
        {MENU.map((item) => (
          <NavLink key={item.to} to={item.to} onClick={() => setMenuOpen(false)} className={({ isActive }) => (isActive ? "active" : "")}>
            {item.label}
            {item.badge === "support" && unread > 0 && <span className="nav-badge">{unread}</span>}
            {item.badge === "retake" && pendingRetake > 0 && <span className="nav-badge">{pendingRetake}</span>}
          </NavLink>
        ))}
        <div className="logout-btn">
          <button className="btn btn-secondary btn-block" onClick={handleLogout}>Keluar</button>
        </div>
      </aside>
      {menuOpen && <div className="admin-backdrop" onClick={() => setMenuOpen(false)} aria-hidden="true" />}
      <main className="admin-main">
        <div className="admin-bar">
          <button
            type="button"
            className="menu-btn"
            aria-label={menuOpen ? "Tutup menu" : "Buka menu"}
            aria-expanded={menuOpen}
            aria-controls="admin-menu"
            onClick={() => setMenuOpen((v) => !v)}
          >
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16" /></svg>
          </button>
          <span className="admin-avatar" aria-hidden="true">{(username ?? "?").slice(0, 1).toUpperCase()}</span>
          <div>
            <strong>{username}</strong>
            <span>{role === "superadmin" ? "Super admin" : "Admin"}</span>
          </div>
        </div>
        <Outlet />
      </main>
    </div>
  );
}
