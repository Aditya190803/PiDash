import json
from app import create_app


def test_api_create_with_unusual_content_type(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()

    app = create_app({"TESTING": True, "UPLOAD_FOLDER": str(uploads), "SECRET_KEY": "test"})
    client = app.test_client()

    # Send JSON payload but with an unusual content-type that some clients send
    resp = client.post("/api/create", data=json.dumps({"path": "", "type": "folder", "name": "weird"}), content_type="application/octet-stream")
    assert resp.status_code == 200
    assert (uploads / "weird").is_dir()

    # Also test urlencoded raw body with text/plain content type
    resp = client.post("/api/create", data="path=&type=file&name=plainfile.txt", content_type="text/plain")
    assert resp.status_code == 200
    assert (uploads / "plainfile.txt").exists()
