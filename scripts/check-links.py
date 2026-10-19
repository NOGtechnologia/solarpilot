"""Prüft relative Links und Bilder in allen Markdown-Dateien (vor dem Veröffentlichen ausführen).

    python scripts/check-links.py
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP = {"node_modules", ".venv", ".next", "out", ".git"}
LINK = re.compile(r'(?:\]\(|src=")([^)"#\s]+)')

bad = 0
for md in ROOT.rglob("*.md"):
    if SKIP & set(md.relative_to(ROOT).parts):
        continue
    for m in LINK.finditer(md.read_text(encoding="utf-8")):
        link = m.group(1)
        if link.startswith(("http://", "https://", "mailto:", "../../")):
            continue  # extern bzw. GitHub-relative Links (Actions, Security)
        if not (md.parent / link).resolve().exists():
            print(f"{md.relative_to(ROOT)}: {link}")
            bad += 1
print("OK – keine toten Links" if not bad else f"{bad} tote Links")
sys.exit(1 if bad else 0)
