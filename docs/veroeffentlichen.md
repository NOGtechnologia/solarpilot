# SolarPilot auf GitHub veröffentlichen

Schritt-für-Schritt-Anleitung für den ersten Upload. Dauer: ca. 15 Minuten.
Alle Texte zum Kopieren stehen in den grauen Kästen.

## 0. Vorab prüfen (lokal)

```bash
python scripts/check-links.py          # keine toten Links in der Doku
cd backend && pytest && cd ..           # 70+ Tests grün
cd frontend && npm test && npm run build && cd ..
```

Zusätzlich empfohlen: Secret-Scan mit [gitleaks](https://github.com/gitleaks/gitleaks) – `gitleaks git .` muss
„no leaks found“ melden. Die CI prüft das bei jedem Push erneut.

> **Datenschutz:** Die bisherigen Commits enthalten deine E-Mail-Adresse als Autor. Sie wird mit dem
> Repo öffentlich. Wer das nicht möchte, stellt vor dem ersten Push auf die GitHub-No-Reply-Adresse um
> (GitHub → Settings → Emails → „Keep my email addresses private“) und schreibt die Autorenangaben um:
>
> ```bash
> git config user.email "<ID>+<name>@users.noreply.github.com"
> git rebase -r --root --exec "git commit --amend --no-edit --reset-author"
> ```

## 1. Repository auf GitHub anlegen

1. https://github.com/new öffnen
2. **Repository name:** `solarpilot`
3. **Description** (kopieren):

   ```
   ☀️ Open-Source-Dashboard für PV-Anlagen aller Hersteller – Live-Energiefluss, PV-Prognose, Strompreise und Tipps. Self-hosted mit Docker, läuft auf dem Raspberry Pi.
   ```

4. **Public** wählen, **kein** README/.gitignore/Lizenz anhaken (ist alles schon da) → *Create repository*

## 2. Repo-Namen eintragen und hochladen

Den Platzhalter `NOGtechnologia/solarpilot` (Badges, Links, Docker-Image) durch deinen GitHub-Pfad ersetzen:

```bash
python scripts/set-repo.py <dein-github-name>/solarpilot
git add -A && git commit -m "chore: GitHub-Pfad gesetzt"
git remote add origin https://github.com/<dein-github-name>/solarpilot.git
git push -u origin main
```

## 3. Repo-Einstellungen

**About** (Zahnrad rechts auf der Repo-Startseite):

- **Website:** leer lassen oder später die Live-Demo
- **Topics** (einzeln eintragen):

  ```
  solar photovoltaics pv dashboard home-assistant energy self-hosted raspberry-pi
  inverter modbus sunspec mqtt fronius sma solaredge victron opendtu fastapi nextjs
  ```

- Haken bei *Releases* und *Packages*

**Social Preview:** *Settings → General → Social preview → Edit* → `docs/images/social-preview.png`
(1280 × 640 px) hochladen. Das ist das Bild, das bei Links auf X, Mastodon, Reddit usw. erscheint.

**Features** (*Settings → General*): *Issues* ✓, *Discussions* ✓ (für Fragen zu Geräten), *Wiki* ✗.

**Sicherheit** (*Settings → Code security*): *Dependabot alerts* ✓, *Secret scanning* ✓,
*Private vulnerability reporting* ✓ (wird in `SECURITY.md` verlinkt).

**Actions** (*Settings → Actions → General*): *Workflow permissions* → „Read and write permissions“
(nötig, damit der Release-Workflow das Docker-Image und das Release anlegen darf).

## 4. Erstes Release v1.0.0

Nach dem Push läuft die CI (Tab *Actions*) – warten, bis alles grün ist. Dann:

```bash
git tag -a v1.0.0 -m "SolarPilot 1.0.0"
git push origin v1.0.0
```

Der Workflow *Release* baut das Multi-Arch-Image (amd64 + arm64, ca. 15–25 Minuten) und legt das GitHub-Release
mit dem Changelog an. Danach:

1. *Packages* → `solarpilot` → *Package settings* → **Change visibility → Public**
   (sonst kann niemand `docker pull ghcr.io/nogtechnologia/solarpilot` ausführen)
2. Release öffnen → *Edit* → Screenshots aus `docs/images/` per Drag & Drop ergänzen → *Update release*

Text für die Release-Beschreibung (oben einfügen):

```markdown
## ☀️ SolarPilot 1.0.0 – erste öffentliche Version

Open-Source-Dashboard für PV-Anlagen: Live-Energiefluss, 7-Tage-PV-Prognose, Börsenstrompreise,
Solar-News und konkrete Tipps – für SMA, Fronius, SolarEdge, Kostal, Huawei, Victron, Enphase, GoodWe,
OpenDTU, Shelly, MQTT und Home Assistant.

**Schnellstart:** `docker compose up -d` → http://localhost:8080 → „Demo starten“

Docker-Image: `ghcr.io/nogtechnologia/solarpilot:1.0.0` (amd64 + arm64 / Raspberry Pi)
```

## 5. Bekannt machen

Vorschläge für Beiträge (immer mit Screenshot `docs/images/dashboard-dark.png`):

| Wo | Hinweis |
| --- | --- |
| [Photovoltaikforum](https://www.photovoltaikforum.com) | Bereich „Software / Monitoring“, auf Deutsch, Hersteller-Liste nennen |
| r/selfhosted | Titel: *SolarPilot – self-hosted PV dashboard (SMA, Fronius, Huawei, Victron, OpenDTU …)* |
| r/solar, r/homeassistant | Fokus auf Prognose, Tipps und MQTT-Discovery |
| Home Assistant Community | Kategorie *Share your Projects* |

Kurztext zum Kopieren:

```
Ich habe SolarPilot veröffentlicht – ein Open-Source-Dashboard für PV-Anlagen. Es verbindet sich lokal
mit SMA, Fronius, SolarEdge, Huawei, Victron, OpenDTU u. a., zeigt den Energiefluss live, eine 7-Tage-PV-
Prognose, Börsenstrompreise und gibt Tipps (z. B. beste Zeit für Waschmaschine/E-Auto). Läuft per Docker
auf dem Raspberry Pi. Feedback und Tests mit echten Anlagen sind sehr willkommen!
https://github.com/NOGtechnologia/solarpilot
```

## 6. Danach

- Issues schnell beantworten – Rückmeldungen von echten Anlagen machen Adapter von „beta“ zu „stabil“
- Neue Versionen: `CHANGELOG.md` ergänzen, Version in `backend/app/__init__.py`, `backend/pyproject.toml`
  und `frontend/package.json` anheben, Tag `vX.Y.Z` pushen
- Optional Live-Demo: Image mit `SOLARPILOT_DEMO=true` und aktiviertem *öffentlichem Dashboard* auf einem
  kleinen Server betreiben und die URL im *About*-Feld eintragen
