import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { adminLogin } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { useAdminAuth } from "../../context/AdminAuthContext";
import { BrandMark } from "../../components/PublicHeader";
import { ReadScene } from "../../components/Illustrations";

export default function AdminLogin() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login } = useAdminAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await adminLogin(username, password);
      login(res.access_token, res.username, res.role);
      navigate("/admin/dashboard");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <aside className="auth-side">
        <div className="lp-brand"><BrandMark />Ruang <em>Admin</em></div>
        <div>
          <h2>Selamat datang kembali.</h2>
          <p>Kelola peserta, pertanyaan, dan hasil skrining dari satu tempat.</p>
        </div>
        <div className="auth-art"><ReadScene /></div>
      </aside>
      <main className="auth-form">
        <div className="auth-card">
          <h1>Masuk</h1>
          <p className="page-lead">Gunakan akun admin yang diberikan kepadamu.</p>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="adm-user">Nama pengguna</label>
              <input id="adm-user" className="form-control" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
            </div>
            <div className="form-group">
              <label htmlFor="adm-pass">Kata sandi</label>
              <input id="adm-pass" type="password" className="form-control" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            {error && <div className="notice notice-danger" role="alert">{error}</div>}
            <button className="btn btn-primary btn-block btn-lg" disabled={loading} type="submit">
              {loading ? "Sebentar ya..." : "Masuk"}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
