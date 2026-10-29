import { createContext, useContext, useState } from "react";
import type { ReactNode } from "react";

interface AdminAuthState {
  token: string | null;
  username: string | null;
  role: string | null;
  login: (token: string, username: string, role: string) => void;
  logout: () => void;
}

const AdminAuthContext = createContext<AdminAuthState | undefined>(undefined);

export function AdminAuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem("admin_token"));
  const [username, setUsername] = useState<string | null>(localStorage.getItem("admin_username"));
  const [role, setRole] = useState<string | null>(localStorage.getItem("admin_role"));

  const login = (t: string, u: string, r: string) => {
    localStorage.setItem("admin_token", t);
    localStorage.setItem("admin_username", u);
    localStorage.setItem("admin_role", r);
    setToken(t);
    setUsername(u);
    setRole(r);
  };

  const logout = () => {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_username");
    localStorage.removeItem("admin_role");
    setToken(null);
    setUsername(null);
    setRole(null);
  };

  return (
    <AdminAuthContext.Provider value={{ token, username, role, login, logout }}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  const ctx = useContext(AdminAuthContext);
  if (!ctx) throw new Error("useAdminAuth must be used within AdminAuthProvider");
  return ctx;
}
