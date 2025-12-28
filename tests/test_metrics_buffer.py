import time

from app.metrics_buffer import MetricsBuffer


def test_append_and_clear():
    b = MetricsBuffer(sample_interval=1, max_seconds=60)
    b.clear()
    b.append_sample({"cpu_usage": 1, "ram_usage": 2, "disk_usage": 3}, ts=1000)
    assert len(b._dq) == 1
    b.clear()
    assert len(b._dq) == 0


def test_get_history_aggregation(monkeypatch):
    b = MetricsBuffer(sample_interval=1, max_seconds=300)
    b.clear()
    b.append_sample({"cpu_usage": 10, "ram_usage": 30, "disk_usage": 5}, ts=1000)
    b.append_sample({"cpu_usage": 20, "ram_usage": 40, "disk_usage": 15}, ts=1003)
    # Make "now" 1006 so both samples fall within the last 1 minute window
    monkeypatch.setattr('time.time', lambda: 1006)
    hist = b.get_history(minutes=1, step=5)
    assert isinstance(hist, list)
    assert len(hist) == 1
    assert hist[0]["cpu_usage"] == 15.0
    assert hist[0]["ram_usage"] == 35.0
    assert hist[0]["disk_usage"] == 10.0
