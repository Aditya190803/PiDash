import os
from app import create_app


def test_open_file_serves_content(tmp_path, monkeypatch):
    # Create a test upload folder and a sample file
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    file_path = upload_dir / "hello.txt"
    file_path.write_text("hello world")

    app = create_app({"TESTING": True, "UPLOAD_FOLDER": str(upload_dir)})
    client = app.test_client()

    resp = client.get("/open/hello.txt")
    assert resp.status_code == 200
    assert resp.data == b"hello world"


def test_index_links_to_file_manager():
    app = create_app({"TESTING": True})
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    # File Manager quick link should be present in the default setup
    assert b"/file-manager" in resp.data


def test_file_manager_has_open_link(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    (upload_dir / "sample.txt").write_text("sample")

    app = create_app({"TESTING": True, "UPLOAD_FOLDER": str(upload_dir)})
    client = app.test_client()
    resp = client.get("/file-manager")
    assert resp.status_code == 200
    assert b"/open/" in resp.data
    assert b'target="_blank"' in resp.data


def test_api_create_items(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()

    app = create_app({"TESTING": True, "UPLOAD_FOLDER": str(uploads), "SECRET_KEY": "test"})
    client = app.test_client()

    # Create folder via JSON
    resp = client.post("/api/create", json={"path": "", "type": "folder", "name": "newdir"})
    assert resp.status_code == 200
    assert (uploads / "newdir").is_dir()

    # Create file via JSON inside newdir
    resp = client.post("/api/create", json={"path": "newdir", "type": "file", "name": "file.txt"})
    assert resp.status_code == 200
    assert (uploads / "newdir" / "file.txt").exists()

    # Create folder via form-encoded data
    resp = client.post("/api/create", data={"path": "", "type": "folder", "name": "formdir"}, content_type="application/x-www-form-urlencoded")
    assert resp.status_code == 200
    assert (uploads / "formdir").is_dir()

    # Create file via multipart/form-data (as if a browser form / FormData was used)
    resp = client.post("/api/create", data={"path": "formdir", "type": "file", "name": "formfile.txt"}, content_type="multipart/form-data")
    assert resp.status_code == 200
    assert (uploads / "formdir" / "formfile.txt").exists()


def test_api_delete_and_move(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()

    # Create nested folder with a file inside
    (uploads / "todel").mkdir()
    (uploads / "todel" / "inner.txt").write_text("hi")

    app = create_app({"TESTING": True, "UPLOAD_FOLDER": str(uploads), "SECRET_KEY": "test"})
    client = app.test_client()

    # Attempt to delete non-empty directory without recursive -> should fail with 400
    resp = client.post("/api/delete", json={"path": "todel"})
    assert resp.status_code == 400

    # Now delete recursively
    resp = client.post("/api/delete", json={"path": "todel", "recursive": True})
    assert resp.status_code == 200
    assert not (uploads / "todel").exists()

    # Test renaming/moving a file
    (uploads / "a").mkdir()
    (uploads / "a" / "f.txt").write_text("x")
    resp = client.post("/api/rename", json={"old_path": "a/f.txt", "new_path": "b/g.txt"})
    assert resp.status_code == 200
    assert (uploads / "b" / "g.txt").exists()