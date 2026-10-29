import { useEffect, useState } from "react";
import {
  listQuestions, createQuestion, updateQuestion, deleteQuestion, listPositions,
} from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { Spinner, EmptyState, ConfirmDialog, useToast } from "../../components/Common";
import type { QuestionAdmin, Position } from "../../api/types";

type Code = "A" | "B" | "C" | "D";
interface OptionForm { option_code: Code; option_text: string; score: number; }

const CODES: Code[] = ["A", "B", "C", "D"];
const emptyOptions = (): OptionForm[] => CODES.map((c, i) => ({ option_code: c, option_text: "", score: i }));
const FREQUENCY_TEXTS = ["Tidak pernah", "Kadang-kadang", "Sering", "Sangat sering"];
const MAX_CHIPS = 3;

export default function Questions() {
  const [questions, setQuestions] = useState<QuestionAdmin[] | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<QuestionAdmin | null>(null);
  const [questionText, setQuestionText] = useState("");
  const [options, setOptions] = useState<OptionForm[]>(emptyOptions());
  const [selectedPositions, setSelectedPositions] = useState<string[]>([]);
  const [active, setActive] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<QuestionAdmin | null>(null);

  const { showToast } = useToast();

  const load = () => {
    setQuestions(null);
    listQuestions(page, pageSize)
      .then((res) => { setQuestions(res.items); setTotal(res.total); })
      .catch((err) => { showToast(getErrorMessage(err), "error"); setQuestions([]); });
  };

  useEffect(load, [page]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { listPositions().then(setPositions).catch(() => {}); }, []);

  const positionName = (id: string) => positions.find((p) => p.id === id)?.nama_jabatan;

  const openCreate = () => {
    setEditing(null); setQuestionText(""); setOptions(emptyOptions());
    setSelectedPositions([]); setActive(true); setShowForm(true);
  };

  const openEdit = (q: QuestionAdmin) => {
    setEditing(q);
    setQuestionText(q.question_text);
    setOptions(
      CODES.map((code, i) => {
        const found = q.options.find((o) => o.option_code === code);
        return { option_code: code, option_text: found?.option_text ?? "", score: found?.score ?? i };
      })
    );
    setSelectedPositions(q.position_ids);
    setActive(q.active);
    setShowForm(true);
  };

  const setOption = (idx: number, patch: Partial<OptionForm>) =>
    setOptions((prev) => prev.map((o, i) => (i === idx ? { ...o, ...patch } : o)));

  const togglePosition = (id: string) =>
    setSelectedPositions((prev) => (prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]));

  const applyScores = (start: number) => setOptions((prev) => prev.map((o, i) => ({ ...o, score: start + i })));
  const applyFrequencyTexts = () => setOptions((prev) => prev.map((o, i) => ({ ...o, option_text: FREQUENCY_TEXTS[i] })));

  const handleSave = async () => {
    if (!questionText.trim()) { showToast("Teks pertanyaan wajib diisi", "error"); return; }
    if (options.some((o) => !o.option_text.trim())) { showToast("Semua pilihan A, B, C, dan D wajib diisi", "error"); return; }

    setSaving(true);
    try {
      const payload = {
        question_text: questionText.trim(),
        active,
        position_ids: selectedPositions,
        options: options.map((o, idx) => ({ ...o, order_number: idx })),
      };
      if (editing) {
        await updateQuestion(editing.id, payload);
        showToast("Pertanyaan disimpan", "success");
      } else {
        await createQuestion(payload);
        showToast("Pertanyaan ditambahkan", "success");
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
      await deleteQuestion(deleteTarget.id);
      showToast("Pertanyaan dihapus", "success");
      setDeleteTarget(null);
      load();
    } catch (err) {
      showToast(getErrorMessage(err), "error");
    }
  };

  const toggleActive = async (q: QuestionAdmin) => {
    try {
      await updateQuestion(q.id, { active: !q.active });
      showToast(`Pertanyaan ${!q.active ? "diaktifkan" : "dinonaktifkan"}`, "success");
      load();
    } catch (err) {
      showToast(getErrorMessage(err), "error");
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const allSelected = positions.length > 0 && selectedPositions.length === positions.length;

  return (
    <div>
      <div className="admin-topbar">
        <div>
          <h1 style={{ marginBottom: 4 }}>Pertanyaan skrining</h1>
          <p className="page-sub">{total} pertanyaan. Perubahan langsung dipakai peserta berikutnya.</p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>+ Tambah pertanyaan</button>
      </div>

      {!questions ? <Spinner /> : questions.length === 0 ? <EmptyState message="Belum ada pertanyaan. Klik Tambah pertanyaan untuk mulai." /> : (
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Pertanyaan</th><th>Jabatan</th><th>Status</th><th>Aksi</th></tr></thead>
            <tbody>
              {questions.map((q) => {
                const names = q.position_ids.map(positionName).filter(Boolean) as string[];
                return (
                  <tr key={q.id}>
                    <td><div className="q-text">{q.question_text}</div></td>
                    <td>
                      {names.length === 0 ? <span className="chip-mini muted">Umum</span> : (
                        <>
                          {names.slice(0, MAX_CHIPS).map((n) => <span className="chip-mini" key={n}>{n}</span>)}
                          {names.length > MAX_CHIPS && (
                            <span className="chip-mini muted" title={names.slice(MAX_CHIPS).join(", ")}>+{names.length - MAX_CHIPS}</span>
                          )}
                        </>
                      )}
                    </td>
                    <td><span className={`badge ${q.active ? "badge-success" : "badge-muted"}`}>{q.active ? "Aktif" : "Nonaktif"}</span></td>
                    <td>
                      <div className="row-actions">
                        <button className="btn btn-secondary btn-sm" onClick={() => openEdit(q)}>Edit</button>
                        <button className="btn btn-secondary btn-sm" onClick={() => toggleActive(q)}>{q.active ? "Nonaktifkan" : "Aktifkan"}</button>
                        <button className="btn btn-danger btn-sm" onClick={() => setDeleteTarget(q)}>Hapus</button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="pagination">
        <button className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Sebelumnya</button>
        <span>Halaman {page} dari {totalPages}</span>
        <button className="btn btn-secondary btn-sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Berikutnya</button>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal modal-lg" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3>{editing ? "Edit pertanyaan" : "Tambah pertanyaan"}</h3>
              <button className="icon-btn" aria-label="Tutup" onClick={() => setShowForm(false)}>×</button>
            </div>

            <div className="modal-body">
              <section>
                <div className="section-head"><span className="section-title">Teks pertanyaan</span></div>
                <textarea
                  className="form-control" rows={3} autoFocus
                  placeholder="Contoh: Saya merasa terbebani oleh pekerjaan saya."
                  value={questionText} onChange={(e) => setQuestionText(e.target.value)}
                />
              </section>

              <section>
                <div className="section-head">
                  <span className="section-title">Pilihan jawaban dan skor</span>
                  <div className="section-tools">
                    <button type="button" className="link-btn" onClick={applyFrequencyTexts}>Isi skala frekuensi</button>
                    <button type="button" className="link-btn" onClick={() => applyScores(0)}>Skor 0-3</button>
                    <button type="button" className="link-btn" onClick={() => applyScores(1)}>Skor 1-4</button>
                  </div>
                </div>
                <div className="opt-list">
                  <div className="opt-cols"><span /><span>Teks pilihan</span><span>Skor</span></div>
                  {options.map((opt, idx) => (
                    <div className="opt-row" key={opt.option_code}>
                      <span className="opt-badge">{opt.option_code}</span>
                      <input
                        className="form-control" placeholder={`Teks pilihan ${opt.option_code}`}
                        value={opt.option_text} onChange={(e) => setOption(idx, { option_text: e.target.value })}
                      />
                      <input
                        type="number" className="form-control" aria-label={`Skor pilihan ${opt.option_code}`}
                        value={opt.score} onChange={(e) => setOption(idx, { score: Number(e.target.value) })}
                      />
                    </div>
                  ))}
                </div>
              </section>

              <section>
                <div className="section-head">
                  <span className="section-title">Berlaku untuk jabatan</span>
                  <div className="section-tools">
                    <button type="button" className="link-btn" onClick={() => setSelectedPositions(allSelected ? [] : positions.map((p) => p.id))}>
                      {allSelected ? "Kosongkan" : "Pilih semua"}
                    </button>
                  </div>
                </div>
                {positions.length === 0 ? (
                  <p className="form-hint">Belum ada jabatan. Tambahkan dulu di menu Jabatan.</p>
                ) : (
                  <div className="chip-list">
                    {positions.map((p) => (
                      <button type="button" key={p.id} className="chip" aria-pressed={selectedPositions.includes(p.id)} onClick={() => togglePosition(p.id)}>
                        {p.nama_jabatan}
                      </button>
                    ))}
                  </div>
                )}
                {selectedPositions.length === 0 && positions.length > 0 && (
                  <p className="form-hint" style={{ marginTop: 10 }}>
                    Belum ada jabatan dipilih. Pertanyaan ini hanya muncul untuk jabatan yang belum punya pertanyaan khusus.
                  </p>
                )}
              </section>

              <label className="switch-row">
                <div>
                  <strong>Pertanyaan aktif</strong>
                  <span>Nonaktifkan untuk menyembunyikan dari peserta tanpa menghapus.</span>
                </div>
                <input type="checkbox" className="switch-input" checked={active} onChange={(e) => setActive(e.target.checked)} />
              </label>
            </div>

            <div className="modal-foot">
              <button className="btn btn-secondary" onClick={() => setShowForm(false)}>Batal</button>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>{saving ? "Menyimpan..." : "Simpan pertanyaan"}</button>
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        title="Hapus pertanyaan"
        message="Yakin ingin menghapus pertanyaan ini? Jawaban peserta terkait pertanyaan ini juga akan terhapus."
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
