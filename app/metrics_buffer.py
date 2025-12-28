"""Simple in-memory ring buffer for short-term metrics history.

This is intentionally lightweight and dependency-free. It stores timestamped
metric samples in a deque and provides a simple aggregation endpoint to
produce time-bucketed averages suitable for Chart.js.
"""
import time
from collections import deque
from typing import Dict, Any, List, Optional


class MetricsBuffer:
    def __init__(self, sample_interval: float = 1.0, max_seconds: int = 3600):
        self.sample_interval = float(sample_interval)
        self.max_seconds = int(max_seconds)
        # Add a small safety margin (+2) to avoid off-by-one evictions
        self.maxlen = int(self.max_seconds / max(1e-6, self.sample_interval)) + 2
        self._dq = deque(maxlen=self.maxlen)

    def append_sample(self, sample: Dict[str, Any], ts: Optional[float] = None) -> None:
        item = dict(sample) if isinstance(sample, dict) else {"value": sample}
        item["ts"] = ts if ts is not None else time.time()
        self._dq.append(item)

    def clear(self) -> None:
        self._dq.clear()

    def get_history(self, minutes: int = 5, step: int = 1) -> List[Dict[str, Any]]:
        """Return aggregated history for the last `minutes` minutes, bucketed by `step` seconds.

        Each returned item has: ts (epoch seconds, bucket start), cpu_usage, ram_usage, disk_usage, count
        """
        seconds = max(1, int(minutes) * 60)
        now = time.time()
        cutoff = now - seconds
        items = [i for i in list(self._dq) if i.get("ts", 0) >= cutoff]
        if not items:
            return []

        step = max(1, int(step))
        buckets: Dict[int, Dict[str, Any]] = {}
        for i in items:
            b = int(i.get("ts", now)) // step * step
            if b not in buckets:
                buckets[b] = {"count": 0, "cpu": 0.0, "ram": 0.0, "disk": 0.0}
            buckets[b]["count"] += 1
            buckets[b]["cpu"] += float(i.get("cpu_usage", 0))
            buckets[b]["ram"] += float(i.get("ram_usage", 0))
            buckets[b]["disk"] += float(i.get("disk_usage", 0))

        result: List[Dict[str, Any]] = []
        for ts in sorted(buckets.keys()):
            b = buckets[ts]
            result.append({
                "ts": int(ts),
                "cpu_usage": b["cpu"] / b["count"],
                "ram_usage": b["ram"] / b["count"],
                "disk_usage": b["disk"] / b["count"],
                "count": b["count"],
            })
        return result


# Default singleton buffer used by the app
buffer = MetricsBuffer()
