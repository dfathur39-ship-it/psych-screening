import type { ReactNode } from "react";
import { BrandMark } from "./PublicHeader";

export const KTP_STEPS = ["Foto KTP", "Periksa data"];

function Check() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12.5l4.5 4.5L19 7.5" />
    </svg>
  );
}

export function Stepper({ current, steps = KTP_STEPS }: { current: number; steps?: string[] }) {
  return (
    <ol className="stepper" aria-label="Langkah">
      {steps.map((label, i) => {
        const n = i + 1;
        const state = n < current ? "done" : n === current ? "current" : "todo";
        return (
          <li key={label} className={`stepper-item ${state}`} aria-current={state === "current" ? "step" : undefined}>
            <span className="stepper-dot">{state === "done" ? <Check /> : n}</span>
            <span className="stepper-label">{label}</span>
          </li>
        );
      })}
    </ol>
  );
}

/** Shared shell for focused pages: brand header, optional step indicator, animated card.
 *  The brand is deliberately not a link so a participant can't leave mid-screening by accident.
 *  `embedded` drops the header and page wrapper for pages already inside MemberLayout. */
export default function FlowLayout({
  step, steps, wide = false, embedded = false, children,
}: { step?: number; steps?: string[]; wide?: boolean; embedded?: boolean; children: ReactNode }) {
  const main = (
    <main className={`flow-main ${wide ? "wide" : ""}`}>
      {step !== undefined && <Stepper current={step} steps={steps} />}
      <div className="flow-card rise">{children}</div>
    </main>
  );
  if (embedded) return main;
  return (
    <div className="lp">
      <header className="lp-nav">
        <div className="lp-brand"><BrandMark />Skrining <em>Psikologi</em></div>
      </header>
      {main}
    </div>
  );
}
