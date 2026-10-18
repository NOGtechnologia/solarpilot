import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="solarpilot-test-")
os.environ["SOLARPILOT_DATA_DIR"] = _tmp
os.environ["SOLARPILOT_DATABASE_URL"] = "sqlite://"
os.environ["SOLARPILOT_SCHEDULER_ENABLED"] = "false"
os.environ["SOLARPILOT_SECRET_KEY"] = "test-secret-key-for-solarpilot-tests"
os.environ["SOLARPILOT_DEMO"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.auth import limiter  # noqa: E402
from app.db import create_db, init_engine, new_session  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services import cache  # noqa: E402


@pytest.fixture(autouse=True)
def _reset():
    cache.clear()
    limiter.fails.clear()
    yield


@pytest.fixture
def db():
    init_engine("sqlite://")
    create_db()
    with new_session() as s:
        yield s


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin(client):
    r = client.post("/api/auth/setup", json={"username": "admin", "password": "secret123"})
    assert r.status_code == 200
    return client
