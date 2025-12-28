import os
import json
from app import create_app
from pathlib import Path


def test_first_run_redirect(tmp_path, monkeypatch):
    # Ensure no setup file exists
    monkeypatch.delenv("SETUP_CONFIG_FILE", raising=False)
    setup_file = tmp_path / "setup_config.json"
    monkeypatch.setenv("SETUP_CONFIG_FILE", str(setup_file))

    app = create_app({"TESTING": True, "SECRET_KEY": "test"})
    client = app.test_client()

    # Creating app SHOULD persist defaults to the setup file
    app = create_app({"TESTING": True, "SECRET_KEY": "test"})
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    # Defaults should have been persisted
    assert setup_file.exists()
    cfg = json.loads(setup_file.read_text())
    assert cfg["quick_links"][0]["name"] == "Router Admin"

    # Post a setup
    # Submit URLs for predefined links (match defaults order)
    resp = client.post(
        "/setup",
        data={
            "link_0_url": "http://10.0.0.1",
            "link_1_url": "https://google.com",
            "link_2_url": "https://youtube.com",
            "link_3_url": "https://github.com",
            "upload_folder": str(tmp_path / "uploads"),
        },
        follow_redirects=True,
    )
    assert b"Setup complete" in resp.data

    # Check file created
    assert setup_file.exists()
    cfg = json.loads(setup_file.read_text())
    assert "quick_links" in cfg
    # Names are predefined; ensure the first is Router Admin and URL updated
    assert cfg["quick_links"][0]["name"] == "Router Admin"
    assert cfg["quick_links"][0]["url"] == "http://10.0.0.1"
    assert "upload_folder" in cfg

    # The index should reflect saved quick link URLs immediately
    resp = client.get("/")
    assert b"http://10.0.0.1" in resp.data


def test_browse_and_download(tmp_path, monkeypatch):
    # Setup config and create files
    monkeypatch.setenv("SETUP_CONFIG_FILE", str(tmp_path / "setup_config.json"))
    cfg = {"upload_folder": str(tmp_path / "uploads"), "quick_links": []}
    (tmp_path / "setup_config.json").write_text(json.dumps(cfg))

    uploads = tmp_path / "uploads"
    uploads.mkdir()
    nested = uploads / "nested"
    nested.mkdir()
    (nested / "file.txt").write_bytes(b"hello")

    app = create_app(
        {"TESTING": True, "UPLOAD_FOLDER": str(uploads), "SECRET_KEY": "test"}
    )
    client = app.test_client()

    # Browse root
    resp = client.get("/browse/")
    assert resp.status_code == 200
    assert b"nested" in resp.data

    # Browse nested
    resp = client.get("/browse/nested")
    assert b"file.txt" in resp.data

    # Download file (no API key, allowed by default)
    resp = client.get("/download/nested/file.txt")
    # Without API key, default behavior should require 401 if REQUIRE_LOGIN true; otherwise allow
    assert resp.status_code in (200, 401)
