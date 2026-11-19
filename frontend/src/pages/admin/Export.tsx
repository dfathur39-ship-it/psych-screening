import { useState } from "react";
import { downloadExport } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { useToast } from "../../components/Common";

export default function Export() {
  const [loading, setLoading] = useState<"csv" | "excel" | "pdf" | null>(null);
  const { showToast } = useToast();

  const handleExport = async (format: "csv" | "excel" | "pdf") => {
    setLoading(format);
    try {
      await downloadExport(format);
      showToast("Data berhasil diunduh", "success");
    } catch (err) {
      showToast(getErrorMessage(err), "error");
    } finally {
      setLoading(null);
    }
  };

  return (
    <div>
      <div className="admin-topbar"><h1>Ekspor Data</h1></div>
      <div className="card" style={{ maxWidth: 560 }}>
        <p>
          Unduh data hasil skrining yang sudah selesai dalam format CSV, Excel, atau PDF.
          Kolom: No, Nama, Usia, Jabatan, Email, No HP, Mulai, Selesai, Durasi, Score, Kategori.
          Waktu dalam WIB.
        </p>
        <p className="form-hint">NIK tidak disertakan dalam export demi privasi data.</p>
        <div style={{ display: "flex", gap: 10, marginTop: 16, flexWrap: "wrap" }}>
          <button className="btn btn-primary" onClick={() => handleExport("csv")} disabled={loading !== null}>
            {loading === "csv" ? "Sedang mengunduh..." : "Unduh CSV"}
          </button>
          <button className="btn btn-primary" onClick={() => handleExport("excel")} disabled={loading !== null}>
            {loading === "excel" ? "Sedang mengunduh..." : "Unduh Excel"}
          </button>
          <button className="btn btn-primary" onClick={() => handleExport("pdf")} disabled={loading !== null}>
            {loading === "pdf" ? "Sedang mengunduh..." : "Unduh PDF"}
          </button>
        </div>
      </div>
    </div>
  );
}
