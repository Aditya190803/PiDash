import io
import tempfile
import os
from app import create_app


def test_large_upload_rejected():
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "MAX_CONTENT_LENGTH": 1,
            "UPLOAD_FOLDER": tempfile.mkdtemp(),
        }
    )
    client = app.test_client()
    data = {"file": (io.BytesIO(b"x" * 1024), "big.txt")}
    resp = client.post("/api/upload", data=data, content_type="multipart/form-data")
    # Flask should respond with 413 Request Entity Too Large
    assert resp.status_code in (413, 400)


def test_extension_rejection(monkeypatch, tmp_path):
    monkeypatch.setenv("ALLOWED_EXTENSIONS", "txt")
    upload_dir = tmp_path
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "UPLOAD_FOLDER": str(upload_dir),
            "SECRET_KEY": "test",
        }
    )
    client = app.test_client()

    data = {"file": (io.BytesIO(b"hello"), "bad.exe")}
    resp = client.post("/api/upload", data=data, content_type="multipart/form-data")
    result = resp.get_json()
    assert result["error"] == "File type not allowed"
