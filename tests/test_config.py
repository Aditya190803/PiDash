import importlib
import sys
import pytest


def _reload_app_module():
    if 'app' in sys.modules:
        del sys.modules['app']
    return importlib.import_module('app')


def test_raise_on_default_secret_in_production(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.delenv('FLASK_SECRET_KEY', raising=False)
    with pytest.raises(RuntimeError):
        _reload_app_module()


def test_no_raise_when_secret_set(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('FLASK_SECRET_KEY', 'super-secret-key')
    mod = _reload_app_module()
    assert hasattr(mod, 'app')
