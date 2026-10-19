"""Setzt den GitHub-Pfad (Besitzer/Repo) in README, Badges, Doku-Links und User-Agent.

    python scripts/set-repo.py mein-github-name/solarpilot

Ersetzt den Platzhalter ``solarpilot/solarpilot`` in allen versionierten Textdateien.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLACEHOLDER = "solarpilot/solarpilot"
SKIP = {"node_modules", ".venv", ".next", "out", ".git"}
SUFFIXES = {".md", ".py", ".ts", ".tsx", ".yml", ".yaml", ".json", ".mjs", ".toml"}


def main() -> int:
    if len(sys.argv) != 2 or not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+", sys.argv[1]):
        print("Aufruf: python scripts/set-repo.py <besitzer>/<repo>")
        return 2
    slug = sys.argv[1]
    changed = []
    for p in ROOT.rglob("*"):
        rel = p.relative_to(ROOT)
        if not p.is_file() or SKIP & set(rel.parts) or p.suffix not in SUFFIXES:
            continue
        if rel.as_posix() == "scripts/set-repo.py" or rel.name == "package-lock.json":
            continue
        text = p.read_text(encoding="utf-8")
        if PLACEHOLDER in text:
            p.write_text(text.replace(PLACEHOLDER, slug), encoding="utf-8", newline="\n")
            changed.append(rel.as_posix())
    print(f"{len(changed)} Dateien angepasst:", *changed, sep="\n  ")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
