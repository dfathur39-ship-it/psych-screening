import { useEffect, useState } from "react";
import { listAuditLogs } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { Spinner, EmptyState, useToast } from "../../components/Common";

interface AuditRow {
  id: string; admin_username: string; action: string; target_type: string | null;
  target_id: string | null; description: string | null; ip_address: string | null; created_at: string;
}

export default function AuditLogs() {
  const [rows, setRows] = useState<AuditRow[] | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const { showToast } = useToast();
  const pageSize = 25;

  useEffect(() => {
    setRows(null);
    listAuditLogs(page, pageSize)
      .then((res) => { setRows(res.items); setTotal(res.total); })
      .catch((err) => { showToast(getErrorMessage(err), "error"); setRows([]); });
  }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div>
      <div className="admin-topbar"><h1>Riwayat Aktivitas</h1></div>
      {!rows ? <Spinner /> : rows.length === 0 ? <EmptyState message="Belum ada aktivitas yang tercatat" /> : (
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Waktu</th><th>Admin</th><th>Aksi</th><th>Target</th><th>Deskripsi</th><th>IP</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>{new Date(r.created_at).toLocaleString("id-ID")}</td>
                  <td>{r.admin_username}</td>
                  <td>{r.action}</td>
                  <td>{r.target_type ?? "-"}</td>
                  <td>{r.description ?? "-"}</td>
                  <td>{r.ip_address ?? "-"}</td>
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
