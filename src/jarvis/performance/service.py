from __future__ import annotations

from collections import deque
from statistics import median
from threading import Lock
from time import time


class PerformanceMonitor:
    """Small in-memory latency ledger used by Jarvis to watch regressions.

    It intentionally avoids SQLite on the hot path. The UI/runtime can query a
    rolling snapshot while model requests only pay a lock + append cost.
    """

    def __init__(self, max_samples: int = 160):
        self._samples = deque(maxlen=max(20, int(max_samples)))
        self._lock = Lock()
        self._interactive = 0
        self._last_interactive = 0.0

    def begin_interactive(self):
        with self._lock:
            self._interactive += 1
            self._last_interactive = time()

    def end_interactive(self):
        with self._lock:
            self._interactive = max(0, self._interactive - 1)
            self._last_interactive = time()

    def interactive_busy(self, grace_seconds: float = 2.5) -> bool:
        now=time()
        with self._lock:
            return self._interactive > 0 or (now - self._last_interactive) < max(0.0, float(grace_seconds))

    def record(self, *, kind: str, total_ms: float, ttft_ms: float | None = None,
               provider: str | None = None, model: str | None = None,
               route: str | None = None, extra: dict | None = None) -> dict:
        row = {
            "ts": time(),
            "kind": str(kind),
            "total_ms": round(max(0.0, float(total_ms)), 2),
            "ttft_ms": None if ttft_ms is None else round(max(0.0, float(ttft_ms)), 2),
            "provider": provider,
            "model": model,
            "route": route,
            "extra": dict(extra or {}),
        }
        with self._lock:
            self._samples.append(row)
        return row

    @staticmethod
    def _percentile(values, p: float):
        values = sorted(float(v) for v in values if v is not None)
        if not values:
            return None
        if len(values) == 1:
            return round(values[0], 2)
        idx = (len(values) - 1) * p
        lo = int(idx)
        hi = min(len(values) - 1, lo + 1)
        frac = idx - lo
        return round(values[lo] * (1 - frac) + values[hi] * frac, 2)

    def snapshot(self, limit: int = 40) -> dict:
        with self._lock:
            rows = list(self._samples)
        recent = rows[-max(1, int(limit)):]
        chat = [r for r in recent if r.get("kind") in {"chat", "chat_stream"}]
        totals = [r["total_ms"] for r in chat]
        ttfts = [r["ttft_ms"] for r in chat if r.get("ttft_ms") is not None]
        latest = recent[-1] if recent else None
        return {
            "samples": len(rows),
            "interactive_busy": self.interactive_busy(),
            "window": len(recent),
            "chat": {
                "samples": len(chat),
                "median_total_ms": round(median(totals), 2) if totals else None,
                "p95_total_ms": self._percentile(totals, .95),
                "median_ttft_ms": round(median(ttfts), 2) if ttfts else None,
                "p95_ttft_ms": self._percentile(ttfts, .95),
            },
            "latest": latest,
            "recent": recent[-12:],
        }
