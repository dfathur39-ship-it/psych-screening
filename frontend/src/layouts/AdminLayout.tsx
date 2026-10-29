import { useCallback, useState } from "react";
import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import { useAdminAuth } from "../context/AdminAuthContext";
import { adminLogout, getSupportUnread, getRetakePendingCount } from "../api/services";
import { usePolling } from "../hooks/usePolling";

const MENU = [
  { to: "/admin/dashboard", label: "Dashboard" },
  { to: "/admin/participants", label: "Peserta" },
  { to: "/admin/screenings", label: "Skrining" },
  { to: "/admin/support", label: "Pesan", badge: "support" },
  { to: "/admin/retake-requests", label: "Kerjakan Ulang", badge: "retake" },
  { to: "/admin/positions", label: "Jabatan" },
  { to: "/admin/questions", label: "Pertanyaan" },
  { to: "/admin/categories", label: "Kategori Hasil" },
  { to: "/admin/audit-logs", label: "Audit Log" },
  { to: "/admin/export", label: "Export" },
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
        <h2>Skrining Admin</h2>
        {MENU.map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? "active" : "")}>
            {item.label}
            {item.badge === "support" && unread > 0 && <span className="nav-badge">{unread}</span>}
            {item.badge === "retake" && pendingRetake > 0 && <span className="nav-badge">{pendingRetake}</span>}
          </NavLink>
        ))}
        <div className="logout-btn">
          <div style={{ fontSize: 13, opacity: .7, padding: "8px 12px" }}>
            {username} ({role})
          </div>
          <button className="btn btn-secondary btn-block" onClick={handleLogout}>Logout</button>
        </div>
      </aside>
      <main className="admin-main">
        <Outlet />
      </main>
    </div>
  );
}
