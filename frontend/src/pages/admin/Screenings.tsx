import { useEffect, useState } from "react";
import { listAdminScreenings } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { Spinner, EmptyState, useToast } from "../../components/Common";

interface ScreeningRow {
  id: string; participant_nama: string | null; jabatan: string | null;
  total_score: number | null; category: string | null; status: string;
  started_at: string | null; completed_at: string | null;
}

const STATUS_LABEL: Record<string, string> = {
  in_progress: "Sedang Berjalan", completed: "Selesai", abandoned: "Ditinggalkan",
};

const fmtWib = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleString("id-ID", {
        timeZone: "Asia/Jakarta", day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit",
      }) + " WIB"
    : "-";

function duration(start: string | null, end: string | null) {
  if (!start || !end) return "-";
  const secs = Math.max(0, Math.round((new Date(end).getTime() - new Date(start).getTime()) / 1000));
  const h = Math.floor(secs / 3600), m = Math.floor((secs % 3600) / 60), sec = secs % 60;
  return h ? `${h} jam ${m} mnt` : `${m} mnt ${sec} dtk`;
}

export default function Screenings() {
  const [rows, setRows] = useState<ScreeningRow[] | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const { showToast } = useToast();
  const pageSize = 20;

  useEffect(() => {
    setRows(null);
    listAdminScreenings({ page, page_size: pageSize, status: status || undefined })
      .then((res) => { setRows(res.items); setTotal(res.total); })
      .catch((err) => { showToast(getErrorMessage(err), "error"); setRows([]); });
  }, [page, status]); // eslint-disable-line react-hooks/exhaustive-deps

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div>
      <div className="admin-topbar">
        <h1>Data Skrining</h1>
      </div>

      <div className="filters-bar">
        <select className="form-control" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
          <option value="">Semua Status</option>
          <option value="in_progress">Sedang Berjalan</option>
          <option value="completed">Selesai</option>
          <option value="abandoned">Ditinggalkan</option>
        </select>
      </div>

      {!rows ? (
        <Spinner />
      ) : rows.length === 0 ? (
        <EmptyState message="Tidak ada data skrining" />
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr><th>Nama</th><th>Jabatan</th><th>Skor</th><th>Kategori</th><th>Status</th><th>Mulai</th><th>Selesai</th><th>Durasi</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>{r.participant_nama ?? "-"}</td>
                  <td>{r.jabatan ?? "-"}</td>
                  <td>{r.total_score ?? "-"}</td>
                  <td>{r.category ?? "-"}</td>
                  <td><span className={`badge ${r.status === "completed" ? "badge-success" : "badge-warning"}`}>{STATUS_LABEL[r.status] ?? r.status}</span></td>
                  <td>{fmtWib(r.started_at)}</td>
                  <td>{fmtWib(r.completed_at)}</td>
                  <td>{duration(r.started_at, r.completed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="pagination">
        <button className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Sebelumnya</button>
        <span>Halaman {page} dari {totalPages}</span>
        <button className="btn btn-secondary btn-sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Berikutnya</button>
      </div>
    </div>
  );
}
