import os
import json
from app import create_app
from app.auth import create_user


def test_settings_access_control(tmp_path, monkeypatch):
    # Prepare setup config
    monkeypatch.setenv('SETUP_CONFIG_FILE', str(tmp_path / 'setup_config.json'))
    (tmp_path / 'setup_config.json').write_text(json.dumps({'quick_links': [], 'upload_folder': str(tmp_path / 'uploads')}))

    # Create users file and admin
    monkeypatch.setenv('USERS_FILE', str(tmp_path / 'users.json'))
    create_user('admin', 'pwd', role='admin')
    create_user('user', 'pwd', role='user')

    app = create_app({"TESTING": True, "UPLOAD_FOLDER": str(tmp_path / 'uploads'), "SECRET_KEY": "test"})
    client = app.test_client()

    # Non-logged in access -> 401
    resp = client.get('/settings')
    assert resp.status_code == 401

    # Login as non-admin
    client.post('/login', data={'username': 'user', 'password': 'pwd'}, follow_redirects=True)
    resp = client.get('/settings')
    assert resp.status_code == 403

    # Login as admin
    client.post('/login', data={'username': 'admin', 'password': 'pwd'}, follow_redirects=True)
    resp = client.get('/settings')
    assert resp.status_code == 200

    # Post changes
    # Post changes using the predefined links input names
    resp = client.post('/settings', data={'link_0_url': '/a', 'upload_folder': str(tmp_path / 'uploads2')}, follow_redirects=True)
    assert b'Settings saved.' in resp.data

    # Verify setup file updated
    cfg = json.loads((tmp_path / 'setup_config.json').read_text())
    assert cfg['quick_links'][0]['url'] == '/a'
    assert 'upload_folder' in cfg
