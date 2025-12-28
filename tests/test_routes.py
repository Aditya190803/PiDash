import io
import os
import tempfile
from app import app as flask_app


def test_index_renders():
    client = flask_app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"PiDash" in resp.data or b"pi" in resp.data.lower()


def test_health_endpoint():
    client = flask_app.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"
    assert data["service"] == "pidash"


def test_files_upload_and_list(monkeypatch, tmp_path):
    # Use a temporary directory for uploads
    monkeypatch.setenv("UPLOAD_FOLDER", str(tmp_path))
    monkeypatch.setattr(flask_app, "config", dict(flask_app.config))
    flask_app.config["UPLOAD_FOLDER"] = str(tmp_path)

    client = flask_app.test_client()

    # Upload a file using API
    file_content = b"hello world"
    data = {"file": (io.BytesIO(file_content), "test.txt")}
    resp = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200

    # The uploaded file should appear in directory
    files = os.listdir(flask_app.config["UPLOAD_FOLDER"])
    assert "test.txt" in files

    # Ensure GET /file-manager returns 200
    resp = client.get("/file-manager")
    assert resp.status_code == 200
    assert b"test.txt" in resp.data
