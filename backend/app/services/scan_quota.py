"""
Pagar kuota pemanggilan VLM (berbayar) — per peserta dan global, jendela waktu bergulir.
In-memory per proses: cukup untuk satu instance; bila menjalankan banyak worker/instance,
pindahkan ke Redis (batas efektif = batas x jumlah worker).
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class SlidingWindowQuota:
    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def try_acquire(self, key: str, limit: int, window_s: int) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window_s:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


quota = SlidingWindowQuota()
