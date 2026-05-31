import os

# Set required env vars before importing the app
os.environ.setdefault("SECRET_KEY", "test-secret-key-only")
os.environ.setdefault("FLASK_DEBUG", "1")

import pytest
from app import create_app


@pytest.fixture(scope="session")
def app():
    _app = create_app()
    _app.config["TESTING"] = True
    _app.config["WTF_CSRF_ENABLED"] = False
    return _app


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()
