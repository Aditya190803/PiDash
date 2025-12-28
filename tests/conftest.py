import os
import sys

# Ensure project root is on sys.path so tests can import `app` module
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# Provide a test client fixture so tests can use the simple 'client' fixture
# This keeps tests that rely on pytest-flask-like fixtures working without
# adding an extra dependency.
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False, "SECRET_KEY": "test"})
    with app.test_client() as client:
        yield client
