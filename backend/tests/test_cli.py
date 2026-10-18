from sqlmodel import select

from app import cli
from app.auth import hash_password, verify_password
from app.db import new_session
from app.models import Site, User


def test_reset_password(db, monkeypatch):
    monkeypatch.setattr(cli, "_init", lambda: None)
    db.add(User(username="admin", password_hash=hash_password("old-password"), is_admin=True))
    db.commit()
    assert cli.reset_password("admin", "new-password-123") == 0
    with new_session() as s:
        u = s.exec(select(User)).first()
        assert verify_password("new-password-123", u.password_hash)
    assert cli.reset_password("nobody", "whatever-123") == 1
    assert cli.reset_password("admin", "short") == 2


def test_demo_command(db, monkeypatch):
    monkeypatch.setattr(cli, "_init", lambda: None)
    assert cli.main(["demo"]) == 0
    with new_session() as s:
        assert s.exec(select(Site)).first().source == "demo"
