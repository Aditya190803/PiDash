from app import create_app


def test_index_has_chart_placeholder():
    app = create_app({"TESTING": True})
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    # Ensure main System Status section is present
    assert b"System Status" in resp.data


def test_file_manager_has_upload_form():
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    client = app.test_client()
    resp = client.get("/file-manager")
    assert resp.status_code == 200
    assert b"upload-btn" in resp.data or b"Upload" in resp.data
    # File manager should have grid/list views
    assert b"grid-view" in resp.data or b"list-view" in resp.data
