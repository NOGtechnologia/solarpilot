"""Kommandozeile für Betrieb und Notfälle.

python -m app.cli reset-password <benutzer>      # neues Passwort interaktiv setzen
python -m app.cli demo                            # Demo-Anlage anlegen
"""

from __future__ import annotations

import argparse
import getpass
import sys

from sqlmodel import select

from .config import get_settings
from .db import create_db, init_engine, new_session
from .models import User


def _init() -> None:
    s = get_settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    init_engine(s.db_url)
    create_db()


def reset_password(username: str, password: str | None = None) -> int:
    from .auth import hash_password

    _init()
    with new_session() as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if user is None:
            print(f"Benutzer '{username}' nicht gefunden", file=sys.stderr)
            return 1
        if password is None:
            password = getpass.getpass("Neues Passwort (min. 8 Zeichen): ")
        if len(password) < 8:
            print("Passwort zu kurz", file=sys.stderr)
            return 2
        user.password_hash = hash_password(password)
        session.add(user)
        session.commit()
    print("Passwort geändert.")
    return 0


def demo() -> int:
    from .adapters.registry import load_all
    from .services.demo_seed import create_demo_site

    _init()
    load_all()
    with new_session() as session:
        site_id = create_demo_site(session).id
    print(f"Demo-Anlage angelegt (ID {site_id}).")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m app.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    rp = sub.add_parser("reset-password", help="Passwort eines Benutzers neu setzen")
    rp.add_argument("username")
    sub.add_parser("demo", help="Demo-Anlage anlegen")
    args = p.parse_args(argv)
    if args.cmd == "reset-password":
        return reset_password(args.username)
    return demo()


if __name__ == "__main__":
    raise SystemExit(main())
