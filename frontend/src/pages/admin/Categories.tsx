import { useEffect, useState } from "react";
import { listCategories, createCategory, updateCategory, deleteCategory } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { Spinner, EmptyState, ConfirmDialog, useToast } from "../../components/Common";
import type { ResultCategory } from "../../api/types";

const emptyForm = { name: "", min_score: 0, max_score: 10, message: "", recommendation: "", active: true };

export default function Categories() {
  const [categories, setCategories] = useState<ResultCategory[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<ResultCategory | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [deleteTarget, setDeleteTarget] = useState<ResultCategory | null>(null);
  const [saving, setSaving] = useState(false);
  const { showToast } = useToast();

  const load = () => {
    setCategories(null);
    listCategories().then(setCategories).catch((err) => { showToast(getErrorMessage(err), "error"); setCategories([]); });
  };
  useEffect(load, []); // eslint-disable-line react-hooks/exhaustive-deps

  const openCreate = () => { setEditing(null); setForm(emptyForm); setShowForm(true); };
  const openEdit = (c: ResultCategory) => {
    setEditing(c);
    setForm({ name: c.name, min_score: c.min_score, max_score: c.max_score, message: c.message, recommendation: c.recommendation, active: c.active });
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!form.name.trim() || !form.message.trim() || !form.recommendation.trim()) {
      showToast("Nama, pesan, dan rekomendasi wajib diisi", "error"); return;
    }
    if (form.min_score > form.max_score) {
      showToast("Skor minimum tidak boleh lebih besar dari skor maksimum", "error"); return;
    }
    setSaving(true);
    try {
      if (editing) {
        await updateCategory(editing.id, form);
        showToast("Kategori diperbarui", "success");
      } else {
        await createCategory(form);
        showToast("Kategori dibuat", "success");
      }
      setShowForm(false);
      load();
    } catch (err) {
      showToast(getErrorMessage(err), "error");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteCategory(deleteTarget.id);
      showToast("Kategori dihapus", "success");
      setDeleteTarget(null);
      load();
    } catch (err) {
      showToast(getErrorMessage(err), "error");
    }
  };

  return (
    <div>
      <div className="admin-topbar">
        <h1>Kategori Hasil</h1>
        <button className="btn btn-primary" onClick={openCreate}>+ Tambah Kategori</button>
      </div>

      {!categories ? <Spinner /> : categories.length === 0 ? <EmptyState message="Belum ada kategori" /> : (
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Nama</th><th>Rentang Skor</th><th>Pesan</th><th>Status</th><th>Aksi</th></tr></thead>
            <tbody>
              {categories.map((c) => (
                <tr key={c.id}>
                  <td>{c.name}</td>
                  <td>{c.min_score} - {c.max_score}</td>
                  <td>{c.message}</td>
                  <td><span className={`badge ${c.active ? "badge-success" : "badge-muted"}`}>{c.active ? "Aktif" : "Nonaktif"}</span></td>
                  <td style={{ display: "flex", gap: 6 }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => openEdit(c)}>Edit</button>
                    <button className="btn btn-danger btn-sm" onClick={() => setDeleteTarget(c)}>Hapus</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 480 }}>
            <h3>{editing ? "Edit Kategori" : "Tambah Kategori"}</h3>
            <div className="form-group">
              <label>Nama Kategori</label>
              <input className="form-control" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label>Skor Minimum</label>
                <input type="number" className="form-control" value={form.min_score} onChange={(e) => setForm({ ...form, min_score: Number(e.target.value) })} />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label>Skor Maksimum</label>
                <input type="number" className="form-control" value={form.max_score} onChange={(e) => setForm({ ...form, max_score: Number(e.target.value) })} />
              </div>
            </div>
            <div className="form-group">
              <label>Pesan</label>
              <textarea className="form-control" rows={2} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} />
            </div>
            <div className="form-group">
              <label>Rekomendasi</label>
              <textarea className="form-control" rows={2} value={form.recommendation} onChange={(e) => setForm({ ...form, recommendation: e.target.value })} />
            </div>
            <div className="form-group">
              <label><input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} /> Aktif</label>
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowForm(false)}>Batal</button>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>{saving ? "Menyimpan..." : "Simpan"}</button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title="Hapus Kategori"
        message={`Yakin ingin menghapus kategori "${deleteTarget?.name}"?`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
