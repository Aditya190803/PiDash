import os
import io
import tempfile
from app import create_app

from app import create_app
from app.auth import create_user


def test_delete_requires_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv('API_KEY', 'secret123')
    upload_dir = tmp_path
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False, "UPLOAD_FOLDER": str(upload_dir), "SECRET_KEY": "test"})
    client = app.test_client()

    # create a file
    filepath = upload_dir / 'a.txt'
    filepath.write_bytes(b'hello')

    resp = client.post('/delete/a.txt')
    assert resp.status_code == 401

    # now with header
    resp = client.post('/delete/a.txt', headers={'X-API-KEY': 'secret123'}, follow_redirects=True)
    assert resp.status_code == 200
    assert b'has been deleted' in resp.data or b'has been deleted.' in resp.data


def test_download_requires_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv('API_KEY', 'secret123')
    upload_dir = tmp_path
    app = create_app({"TESTING": True, "UPLOAD_FOLDER": str(upload_dir), "SECRET_KEY": "test"})
    client = app.test_client()

    # create a file
    filepath = upload_dir / 'b.txt'
    filepath.write_bytes(b'hello')

    resp = client.get('/download/b.txt')
    assert resp.status_code == 401

    resp = client.get('/download/b.txt', headers={'X-API-KEY': 'secret123'})
    assert resp.status_code == 200
    assert resp.get_data() == b'hello'


def test_require_login_for_delete(monkeypatch, tmp_path):
    # When REQUIRE_LOGIN is true and no API_KEY is set, delete requires a logged-in session
    monkeypatch.setenv('REQUIRE_LOGIN', 'true')
    upload_dir = tmp_path
    app = create_app({"TESTING": True, "UPLOAD_FOLDER": str(upload_dir), "SECRET_KEY": "test", "WTF_CSRF_ENABLED": False})
    client = app.test_client()

    # create a file
    filepath = upload_dir / 'c.txt'
    filepath.write_bytes(b'hello')

    resp = client.post('/delete/c.txt')
    assert resp.status_code == 401


def test_logged_in_user_can_delete(monkeypatch, tmp_path):
    # Create a temporary users file and user
    monkeypatch.setenv('USERS_FILE', str(tmp_path / 'users.json'))
    create_user('admin', 'secret', role='admin')

    upload_dir = tmp_path
    app = create_app({"TESTING": True, "UPLOAD_FOLDER": str(upload_dir), "SECRET_KEY": "test", "WTF_CSRF_ENABLED": False})
    client = app.test_client()

    # create a file
    filepath = upload_dir / 'd.txt'
    filepath.write_bytes(b'hello')

    # login (follow redirect then proceed to delete)
    client.post('/login', data={'username': 'admin', 'password': 'secret'}, follow_redirects=True)

    # now delete without API key
    resp = client.post('/delete/d.txt', follow_redirects=True)
    assert resp.status_code == 200
    assert b'has been deleted' in resp.data or b'has been deleted.' in resp.data


def test_non_admin_cannot_delete(monkeypatch, tmp_path):
    # Create a temporary users file and users
    monkeypatch.setenv('USERS_FILE', str(tmp_path / 'users.json'))
    from app.auth import create_user
    create_user('admin', 'secret', role='admin')
    create_user('user', 'pass', role='user')

    upload_dir = tmp_path
    app = create_app({"TESTING": True, "UPLOAD_FOLDER": str(upload_dir), "SECRET_KEY": "test", "WTF_CSRF_ENABLED": False})
    client = app.test_client()

    # create a file
    filepath = upload_dir / 'e.txt'
    filepath.write_bytes(b'hello')

    # login as non-admin
    client.post('/login', data={'username': 'user', 'password': 'pass'}, follow_redirects=True)

    # attempt delete
    resp = client.post('/delete/e.txt', follow_redirects=True)
    assert resp.status_code == 403 or b'not authorized' in resp.data or b'403' in resp.data

