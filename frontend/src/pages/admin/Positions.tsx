import { useEffect, useState } from "react";
import { listPositions, createPosition, updatePosition, deletePosition } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { Spinner, EmptyState, ConfirmDialog, useToast } from "../../components/Common";
import type { Position } from "../../api/types";

export default function Positions() {
  const [positions, setPositions] = useState<Position[] | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Position | null>(null);
  const [namaJabatan, setNamaJabatan] = useState("");
  const [description, setDescription] = useState("");
  const [active, setActive] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<Position | null>(null);
  const [saving, setSaving] = useState(false);
  const { showToast } = useToast();

  const load = () => {
    setPositions(null);
    listPositions().then(setPositions).catch((err) => { showToast(getErrorMessage(err), "error"); setPositions([]); });
  };

  useEffect(load, []); // eslint-disable-line react-hooks/exhaustive-deps

  const openCreate = () => {
    setEditing(null); setNamaJabatan(""); setDescription(""); setActive(true); setShowForm(true);
  };
  const openEdit = (p: Position) => {
    setEditing(p); setNamaJabatan(p.nama_jabatan); setDescription(p.description ?? ""); setActive(p.active); setShowForm(true);
  };

  const handleSave = async () => {
    if (!namaJabatan.trim()) { showToast("Nama jabatan wajib diisi", "error"); return; }
    setSaving(true);
    try {
      if (editing) {
        await updatePosition(editing.id, { nama_jabatan: namaJabatan.trim(), description, active });
        showToast("Jabatan diperbarui", "success");
      } else {
        await createPosition({ nama_jabatan: namaJabatan.trim(), description, active });
        showToast("Jabatan dibuat", "success");
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
      await deletePosition(deleteTarget.id);
      showToast("Jabatan dihapus", "success");
      setDeleteTarget(null);
      load();
    } catch (err) {
      showToast(getErrorMessage(err), "error");
    }
  };

  return (
    <div>
      <div className="admin-topbar">
        <h1>Jabatan</h1>
        <button className="btn btn-primary" onClick={openCreate}>+ Tambah Jabatan</button>
      </div>

      {!positions ? <Spinner /> : positions.length === 0 ? <EmptyState message="Belum ada jabatan" /> : (
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Nama Jabatan</th><th>Deskripsi</th><th>Jml Pertanyaan</th><th>Status</th><th>Aksi</th></tr></thead>
            <tbody>
              {positions.map((p) => (
                <tr key={p.id}>
                  <td>{p.nama_jabatan}</td>
                  <td>{p.description ?? "-"}</td>
                  <td>{p.question_count}</td>
                  <td><span className={`badge ${p.active ? "badge-success" : "badge-muted"}`}>{p.active ? "Aktif" : "Nonaktif"}</span></td>
                  <td style={{ display: "flex", gap: 6 }}>
                    <button className="btn btn-secondary btn-sm" onClick={() => openEdit(p)}>Edit</button>
                    <button className="btn btn-danger btn-sm" onClick={() => setDeleteTarget(p)}>Hapus</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{editing ? "Edit Jabatan" : "Tambah Jabatan"}</h3>
            <div className="form-group">
              <label>Nama Jabatan</label>
              <input className="form-control" value={namaJabatan} onChange={(e) => setNamaJabatan(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Deskripsi</label>
              <textarea className="form-control" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <div className="form-group">
              <label><input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} /> Aktif</label>
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
        title="Hapus Jabatan"
        message={`Yakin ingin menghapus jabatan "${deleteTarget?.nama_jabatan}"? Pemetaan pertanyaan untuk jabatan ini akan ikut terhapus.`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
