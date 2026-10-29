import { useEffect, useState } from "react";
import { listAdminParticipants } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { Spinner, EmptyState, useToast } from "../../components/Common";

interface ParticipantRow {
  id: string; nama: string; usia: number; jabatan: string;
  no_hp: string; email?: string | null; nik_masked: string | null; created_at: string;
}

export default function Participants() {
  const [rows, setRows] = useState<ParticipantRow[] | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [jabatan, setJabatan] = useState("");
  const { showToast } = useToast();
  const pageSize = 20;

  const load = async () => {
    setRows(null);
    try {
      const res = await listAdminParticipants({
        page, page_size: pageSize,
        search: search || undefined,
        jabatan: jabatan || undefined,
      });
      setRows(res.items);
      setTotal(res.total);
    } catch (err) {
      showToast(getErrorMessage(err), "error");
      setRows([]);
    }
  };

  useEffect(() => { load(); }, [page]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    load();
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div>
      <div className="admin-topbar">
        <h1>Data Peserta</h1>
      </div>

      <form className="filters-bar" onSubmit={handleFilterSubmit}>
        <input className="form-control" placeholder="Cari nama/email/no HP" value={search} onChange={(e) => setSearch(e.target.value)} />
        <input className="form-control" placeholder="Jabatan" value={jabatan} onChange={(e) => setJabatan(e.target.value)} />
        <button className="btn btn-primary" type="submit">Cari</button>
      </form>

      {!rows ? (
        <Spinner />
      ) : rows.length === 0 ? (
        <EmptyState message="Tidak ada data peserta" />
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Nama</th><th>Usia</th><th>Jabatan</th><th>Email</th><th>No HP</th><th>NIK</th><th>Terdaftar</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>{r.nama}</td>
                  <td>{r.usia}</td>
                  <td>{r.jabatan}</td>
                  <td>{r.email ?? "-"}</td>
                  <td>{r.no_hp}</td>
                  <td className="nik-mask">{r.nik_masked ?? "-"}</td>
                  <td>{new Date(r.created_at).toLocaleDateString("id-ID")}</td>
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
