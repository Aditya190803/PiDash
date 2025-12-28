def test_security_headers_present(client):
    resp = client.get('/')
    assert resp.headers.get('X-Content-Type-Options') == 'nosniff'
    assert resp.headers.get('X-Frame-Options') == 'DENY'
    assert 'Content-Security-Policy' in resp.headers
    assert resp.headers.get('Referrer-Policy') == 'no-referrer'
