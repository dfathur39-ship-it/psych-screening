import { useCallback, useEffect, useState } from "react";
import { Spinner, EmptyState, useToast } from "../../components/Common";
import { usePolling } from "../../hooks/usePolling";
import { formatChatTime } from "../../lib/format";
import { listRetakeRequests, decideRetakeRequest } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import type { AdminRetakeRequestItem } from "../../api/types";

type Filter = "pending" | "approved" | "rejected" | "used" | "all";
const FILTERS: { key: Filter; label: string }[] = [
  { key: "pending", label: "Menunggu" },
  { key: "approved", label: "Disetujui" },
  { key: "rejected", label: "Ditolak" },
  { key: "used", label: "Sudah dipakai" },
  { key: "all", label: "Semua" },
];

const STATUS_LABEL: Record<string, string> = {
  pending: "Menunggu persetujuan", approved: "Disetujui", rejected: "Ditolak", used: "Sudah dipakai",
};
const STATUS_BADGE: Record<string, string> = {
  pending: "badge-warning", approved: "badge-success", rejected: "badge-danger", used: "badge-warning",
};

/** Requests from participants who finished a screening and want to redo it.
 *  Approving lets them start exactly one new session; the approval is spent once they do. */
export default function Retake() {
  const { showToast } = useToast();
  const [filter, setFilter] = useState<Filter>("pending");
  const [items, setItems] = useState<AdminRetakeRequestItem[] | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    try {
      setItems((await listRetakeRequests(filter)).items);
    } catch (err) {
      showToast(getErrorMessage(err), "error");
      setItems((prev) => prev ?? []);
    }
  }, [filter, showToast]);

  useEffect(() => { setItems(null); void load(); }, [load]);
  usePolling(load, 8000);

  const decide = async (id: string, status: "approved" | "rejected") => {
    setBusyId(id);
    try {
      await decideRetakeRequest(id, status, notes[id]?.trim() || undefined);
      showToast(status === "approved" ? "Permintaan disetujui" : "Permintaan ditolak", "success");
      void load();
    } catch (err) {
      showToast(getErrorMessage(err), "error");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div>
      <div className="admin-topbar">
        <div>
          <h1 style={{ marginBottom: 4 }}>Permintaan Ulang Skrining</h1>
          <p className="page-sub">Peserta yang sudah selesai skrining dan ingin mengerjakannya lagi.</p>
        </div>
      </div>

      <div className="inbox-tabs" role="tablist" style={{ marginBottom: 16 }}>
        {FILTERS.map((f) => (
          <button key={f.key} role="tab" aria-selected={filter === f.key}
            className={filter === f.key ? "active" : ""} onClick={() => setFilter(f.key)}>
            {f.label}
          </button>
        ))}
      </div>

      {!items ? (
        <Spinner />
      ) : items.length === 0 ? (
        <EmptyState message="Tidak ada permintaan di kategori ini." />
      ) : (
        <div className="retake-list">
          {items.map((r) => (
            <div className="retake-row" key={r.id}>
              <div className="retake-row-head">
                <strong>{r.participant_nama}</strong>
                <span className={`badge ${STATUS_BADGE[r.status]}`}>{STATUS_LABEL[r.status]}</span>
              </div>
              <div className="retake-meta">
                {r.participant_jabatan} · {r.participant_no_hp}{r.participant_email ? ` · ${r.participant_email}` : ""}
              </div>
              <div className="retake-meta">Diajukan {formatChatTime(r.created_at)}</div>
              {r.reason && <p className="retake-reason">"{r.reason}"</p>}
              {r.admin_note && (
                <p className="retake-reason">Catatan admin: {r.admin_note}</p>
              )}
              {r.status === "pending" && (
                <>
                  <div className="form-group" style={{ marginBottom: 8 }}>
                    <input className="form-control" placeholder="Catatan untuk peserta (opsional)"
                      value={notes[r.id] ?? ""} onChange={(e) => setNotes({ ...notes, [r.id]: e.target.value })} />
                  </div>
                  <div className="retake-actions">
                    <button className="btn btn-primary btn-sm" disabled={busyId === r.id} onClick={() => void decide(r.id, "approved")}>
                      Setujui
                    </button>
                    <button className="btn btn-secondary btn-sm" disabled={busyId === r.id} onClick={() => void decide(r.id, "rejected")}>
                      Tolak
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
