from app import create_app


def test_create_app():
    app = create_app({"TESTING": True})
    assert app is not None
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
