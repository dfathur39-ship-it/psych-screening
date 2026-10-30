import { useCallback, useState } from "react";
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
      <aside className="admin-sidebar">
        <div className="lp-brand"><BrandMark />Ruang <em>Admin</em></div>
        {MENU.map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? "active" : "")}>
            {item.label}
            {item.badge === "support" && unread > 0 && <span className="nav-badge">{unread}</span>}
            {item.badge === "retake" && pendingRetake > 0 && <span className="nav-badge">{pendingRetake}</span>}
          </NavLink>
        ))}
        <div className="logout-btn">
          <button className="btn btn-secondary btn-block" onClick={handleLogout}>Keluar</button>
        </div>
      </aside>
      <main className="admin-main">
        <div className="admin-bar">
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
