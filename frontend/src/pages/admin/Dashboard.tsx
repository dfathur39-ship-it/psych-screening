import { useEffect, useState } from "react";
import { getStatistics } from "../../api/services";
import { getErrorMessage } from "../../api/client";
import { Spinner, useToast } from "../../components/Common";
import { DonutChart, BarChart } from "../../components/Charts";
import type { AdminStatistics } from "../../api/types";

function StatIcon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  );
}

const CARDS = [
  { key: "total_participants", label: "Total peserta", color: "var(--chart-1)", d: "M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zM22 21v-2a4 4 0 00-3-3.870M16 3.130a4 4 0 010 7.750" },
  { key: "total_screenings", label: "Total skrining", color: "var(--chart-2)", d: "M9 11l3 3L22 4M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" },
  { key: "total_positions", label: "Total jabatan", color: "var(--chart-3)", d: "M20 7H4a2 2 0 00-2 2v10a2 2 0 002 2h16a2 2 0 002-2V9a2 2 0 00-2-2zM16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16" },
  { key: "total_questions", label: "Total pertanyaan", color: "var(--chart-4)", d: "M12 22a10 10 0 100-20 10 10 0 000 20zM9.090 9a3 3 0 015.830 1c0 2-3 3-3 3M12 17h.010" },
] as const;

export default function Dashboard() {
  const [stats, setStats] = useState<AdminStatistics | null>(null);
  const { showToast } = useToast();

  const load = () => {
    setStats(null);
    getStatistics().then(setStats).catch((err) => showToast(getErrorMessage(err), "error"));
  };

  useEffect(load, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (!stats) return <Spinner label="Memuat statistik..." />;

  return (
    <div>
      <div className="admin-topbar">
        <div>
          <h1 style={{ marginBottom: 4 }}>Dashboard</h1>
          <p className="page-sub">Ringkasan data skrining saat ini</p>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={load}>Muat ulang</button>
      </div>

      <div className="stat-grid">
        {CARDS.map((c) => (
          <div className="stat-card with-icon" key={c.key}>
            <span className="stat-icon" style={{ background: `color-mix(in srgb, ${c.color} 16%, transparent)`, color: c.color }}>
              <StatIcon d={c.d} />
            </span>
            <div>
              <div className="value">{stats[c.key]}</div>
              <div className="label">{c.label}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="dash-grid">
        <section className="panel">
          <div className="panel-head">
            <h3>Hasil skrining</h3>
            <p>Berdasarkan kategori, skrining yang sudah selesai</p>
          </div>
          <DonutChart data={stats.distribusi_kategori} centerLabel="skrining" />
        </section>

        <section className="panel">
          <div className="panel-head">
            <h3>Peserta per jabatan</h3>
            <p>Jabatan dengan skrining terbanyak</p>
          </div>
          <BarChart data={stats.distribusi_jabatan} color="var(--chart-1)" />
        </section>
      </div>
    </div>
  );
}
