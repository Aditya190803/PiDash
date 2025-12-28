import time

from app import create_app
from app.metrics_buffer import buffer


def test_history_endpoint_returns_samples(client):
    # Use the test client; buffer is a singleton that we control directly
    buffer.clear()
    now = time.time()
    buffer.append_sample({"cpu_usage": 5, "ram_usage": 10, "disk_usage": 2}, ts=now - 30)
    buffer.append_sample({"cpu_usage": 15, "ram_usage": 20, "disk_usage": 3}, ts=now - 10)

    resp = client.get('/api/stats/history?minutes=1&step=10')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["minutes"] == 1
    assert data["step"] == 10
    assert "samples" in data
    assert isinstance(data["samples"], list)
    assert len(data["samples"]) >= 1
