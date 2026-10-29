export interface Datum { label: string; value: number }

export const PALETTE = [
  "var(--chart-1)", "var(--chart-2)", "var(--chart-3)",
  "var(--chart-4)", "var(--chart-5)", "var(--chart-6)",
];

/** Keep the top N rows and fold the rest into one "Lainnya" row so charts stay tidy. */
export function topN(data: Datum[], n = 6): Datum[] {
  const sorted = [...data].sort((a, b) => b.value - a.value);
  if (sorted.length <= n) return sorted;
  const head = sorted.slice(0, n - 1);
  const rest = sorted.slice(n - 1).reduce((sum, d) => sum + d.value, 0);
  return [...head, { label: "Lainnya", value: rest }];
}

export function DonutChart({ data, centerLabel }: { data: Datum[]; centerLabel: string }) {
  const rows = topN(data, 6);
  const total = rows.reduce((s, d) => s + d.value, 0);
  if (total === 0) return <div className="panel-empty">Belum ada data</div>;

  const R = 70;
  const C = 2 * Math.PI * R;
  let acc = 0;

  return (
    <div className="donut-wrap">
      <div className="donut">
        <svg viewBox="0 0 180 180" role="img" aria-label={`Distribusi ${centerLabel}`}>
          <circle cx="90" cy="90" r={R} fill="none" stroke="var(--border)" strokeWidth="22" />
          {rows.map((d, i) => {
            const len = (d.value / total) * C;
            const el = (
              <circle
                key={d.label}
                cx="90" cy="90" r={R} fill="none"
                stroke={PALETTE[i % PALETTE.length]} strokeWidth="22"
                strokeDasharray={`${Math.max(len - 2, 0)} ${C - Math.max(len - 2, 0)}`}
                strokeDashoffset={-acc}
              />
            );
            acc += len;
            return el;
          })}
        </svg>
        <div className="donut-center">
          <strong>{total}</strong>
          <span>{centerLabel}</span>
        </div>
      </div>
      <ul className="legend">
        {rows.map((d, i) => (
          <li key={d.label}>
            <span className="dot" style={{ background: PALETTE[i % PALETTE.length] }} />
            <span className="l-label" title={d.label}>{d.label}</span>
            <span className="l-val">{d.value}</span>
            <span className="l-pct">{Math.round((d.value / total) * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function BarChart({ data, color = "var(--chart-1)" }: { data: Datum[]; color?: string }) {
  const rows = topN(data, 6);
  const max = Math.max(1, ...rows.map((d) => d.value));
  if (rows.length === 0) return <div className="panel-empty">Belum ada data</div>;

  return (
    <div className="hbar">
      {rows.map((d) => (
        <div className="hbar-row" key={d.label}>
          <span className="hbar-label" title={d.label}>{d.label}</span>
          <div className="hbar-track">
            <div className="hbar-fill" style={{ width: `${(d.value / max) * 100}%`, background: color }} />
          </div>
          <span className="hbar-val">{d.value}</span>
        </div>
      ))}
    </div>
  );
}
