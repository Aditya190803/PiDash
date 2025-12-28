from app import app as flask_app


def test_metrics_endpoint():
    client = flask_app.test_client()
    resp = client.get("/metrics")
    assert resp.status_code == 200
    content_type = resp.headers.get("Content-Type", "")
    assert "text" in content_type or "application" in content_type
    assert b"pidash_cpu_usage" in resp.data
    assert b"pidash_memory_rss_bytes" in resp.data
    # pidash_process_uptime_seconds may not be present on all platforms; presence is optional
