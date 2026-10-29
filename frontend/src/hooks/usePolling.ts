import { useEffect, useRef } from "react";

/** Calls `fn` every `ms` while the tab is visible, and once when the tab becomes visible again. */
export function usePolling(fn: () => unknown, ms: number, enabled = true) {
  const ref = useRef(fn);
  useEffect(() => { ref.current = fn; });
  useEffect(() => {
    if (!enabled) return;
    const tick = () => { if (document.visibilityState === "visible") void ref.current(); };
    const id = setInterval(tick, ms);
    document.addEventListener("visibilitychange", tick);
    return () => { clearInterval(id); document.removeEventListener("visibilitychange", tick); };
  }, [ms, enabled]);
}
