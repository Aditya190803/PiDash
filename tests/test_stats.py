import json
from app import app as flask_app


def test_api_stats_json():
    client = flask_app.test_client()
    resp = client.get('/api/stats')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'hostname' in data
    assert 'cpu_usage' in data
    assert 'os' in data
    assert 'kernel' in data


def test_api_stats_sse_count_one():
    client = flask_app.test_client()
    # Request a single event and ensure the response is an event stream
    resp = client.get('/api/stats/stream?count=1')
    assert resp.status_code == 200
    content_type = resp.headers.get('Content-Type', '')
    assert content_type.startswith('text/event-stream')

    text = resp.get_data(as_text=True)
    assert 'data:' in text

    # Extract JSON after 'data: '
    idx = text.find('data:')
    payload = text[idx + len('data:'):].strip()
    # If there are multiple lines, only take the first JSON chunk
    payload = payload.split('\n')[0].strip()
    parsed = json.loads(payload)
    assert 'hostname' in parsed
    assert 'cpu_usage' in parsed
    assert 'os' in parsed
    assert 'kernel' in parsed
