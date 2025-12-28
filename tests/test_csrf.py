from io import BytesIO
from app import create_app


def test_csrf_token_present():
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": True, "SECRET_KEY": "test"})
    client = app.test_client()
    r = client.get("/file-manager")
    assert "csrf_token" in r.get_data(as_text=True)


def test_post_without_csrf_fails():
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": True, "SECRET_KEY": "test"})
    client = app.test_client()
    data = {"file": (BytesIO(b"hello"), "a.txt")}
    r = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert r.status_code in (400, 403)
