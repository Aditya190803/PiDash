import io
import tempfile
import os
from app import create_app


def test_upload_missing_part(monkeypatch):
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    client = app.test_client()
    resp = client.post("/api/upload", data={}, content_type="multipart/form-data")
    result = resp.get_json()
    assert result["error"] == "No file part"


def test_delete_nonexistent_file(monkeypatch, tmp_path):
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
    resp = client.post("/delete/nonexistent.txt", follow_redirects=True)
    # Should redirect to file manager (200 status)
    assert resp.status_code == 200
    # Should contain file manager content
    assert b"File Manager" in resp.data


def test_download_nonexistent_file_returns_404():
    app = create_app({"TESTING": True})
    client = app.test_client()
    resp = client.get("/download/nope.txt")
    assert resp.status_code == 404
