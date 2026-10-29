import { useState } from "react";
import type { FormEvent } from "react";
import { useAdminAuth } from "../../context/AdminAuthContext";
import { updateAdminProfile } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { useToast } from "../../components/Common";

export default function AdminProfile() {
  const { username, role, login } = useAdminAuth();
  const { showToast } = useToast();
  const [current, setCurrent] = useState("");
  const [newUsername, setNewUsername] = useState(username ?? "");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const usernameChanged = newUsername.trim() !== "" && newUsername.trim() !== username;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!current) { setError("Masukkan password saat ini untuk menyimpan perubahan."); return; }
    if (!usernameChanged && !newPassword) { setError("Ubah username atau isi password baru."); return; }
    if (newPassword && newPassword.length < 8) { setError("Password baru minimal 8 karakter."); return; }
    if (newPassword && newPassword !== confirm) { setError("Konfirmasi password tidak sama."); return; }
    setSaving(true);
    try {
      const res = await updateAdminProfile({
        current_password: current,
        ...(usernameChanged ? { new_username: newUsername.trim() } : {}),
        ...(newPassword ? { new_password: newPassword } : {}),
      });
      login(res.access_token, res.username, res.role);
      setCurrent(""); setNewPassword(""); setConfirm("");
      setNewUsername(res.username);
      showToast("Profil berhasil diperbarui", "success");
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: 560 }}>
      <div className="admin-topbar">
        <div>
          <h1 style={{ margin: 0 }}>Profil Saya</h1>
          <p className="page-sub">Masuk sebagai <strong>{username}</strong> ({role})</p>
        </div>
      </div>

      <form className="card" onSubmit={handleSubmit} noValidate>
        <div className="form-group">
          <label htmlFor="ap-username">Username</label>
          <input id="ap-username" className="form-control" value={newUsername} autoComplete="username"
            onChange={(e) => setNewUsername(e.target.value)} />
          <div className="form-hint">Huruf, angka, titik, garis bawah, @, atau strip. Minimal 3 karakter.</div>
        </div>

        <div className="form-group">
          <label htmlFor="ap-new">Password baru</label>
          <input id="ap-new" type="password" className="form-control" value={newPassword} autoComplete="new-password"
            placeholder="Kosongkan bila tidak diganti" onChange={(e) => setNewPassword(e.target.value)} />
          <div className="form-hint">Minimal 8 karakter.</div>
        </div>

        {newPassword && (
          <div className="form-group">
            <label htmlFor="ap-confirm">Ulangi password baru</label>
            <input id="ap-confirm" type="password" className="form-control" value={confirm} autoComplete="new-password"
              onChange={(e) => setConfirm(e.target.value)} />
          </div>
        )}

        <div className="form-section" style={{ marginTop: 20 }}>
          <div className="form-group">
            <label htmlFor="ap-current">Password saat ini</label>
            <input id="ap-current" type="password" className="form-control" value={current} autoComplete="current-password"
              onChange={(e) => setCurrent(e.target.value)} />
            <div className="form-hint">Wajib diisi untuk menyimpan perubahan apa pun.</div>
          </div>
        </div>

        {error && <div className="notice notice-danger" role="alert">{error}</div>}

        <button className="btn btn-primary" type="submit" disabled={saving}>
          {saving ? "Menyimpan..." : "Simpan perubahan"}
        </button>
      </form>
    </div>
  );
}
