# SolarPilot – Design-System

Ruhig, hochwertig, auf einen Blick lesbar – eher wie eine Apple-Health- oder Tesla-App als wie ein
Technik-Panel. Dieses Dokument ist verbindlich für alle UI-Änderungen.

## Prinzipien

1. **Eine Frage pro Bildschirm-Bereich:** „Was passiert gerade?“ oben (Hero mit Energiefluss),
   „Wie war heute?“ in der Mitte (KPIs, Tagesverlauf), „Was kommt?“ unten (Tipps, Wetter, Preise, News).
2. **Die größte Zahl ist die wichtigste** – die aktuelle PV-Leistung (48–56 px).
3. **Farbe hat Bedeutung, nie Deko.**
4. **Bewegung nur, wo Energie fließt.**
5. **Alles funktioniert ab 360 px Breite.**

## Farben (feste Bedeutung)

| Rolle | Token | Farbe |
| --- | --- | --- |
| Solar / Erzeugung | `--solar` | `#F5A524` |
| Verbrauch | `--load` | `#3B82F6` |
| Batterie | `--battery` | `#22C55E` |
| Netzbezug | `--grid-import` | `#F97316` |
| Einspeisung | `--grid-export` | `#8B5CF6` |
| Hintergrund dunkel / Karte | `--bg` / `--card` | `#0B0F14` / `#121821` |
| Hintergrund hell / Karte | `--bg` / `--card` | `#F7F8FA` / `#FFFFFF` |

Dunkelmodus ist Standard. Text in Amber auf hellem Grund nutzt `--solar-text` (`#9A5B00`), damit
WCAG AA (4,5:1) erfüllt ist. Definiert in `frontend/src/app/globals.css`, in JS in `lib/utils.ts → COLORS`.

## Typografie und Form

- Schrift: **Inter** (`next/font`), Zahlen immer mit `.num` (`tabular-nums`), damit Live-Werte nicht springen
- KPI-Zahlen 28–56 px, Beschriftung 13 px in `--muted`
- Karten: Radius 18 px (`--radius-card`), 1-px-Rand (`--border`) statt schwerer Schatten
- Abstände im 8-px-Raster (Tailwind `gap-2/3/4`, `p-4/5`)

## Signature-Elemente

| Element | Datei |
| --- | --- |
| Animierter Energiefluss (Punkte wandern, Tempo nach Leistung) | `components/dashboard/energy-flow.tsx`, Logik `lib/flow.ts` |
| Sonnenbogen mit Auf-/Untergang | `components/dashboard/sun-arc.tsx` |
| Batterie als Flüssigkeit mit Welle | `components/dashboard/battery-liquid.tsx` |
| Farbverlauf im Kopf nach Tageszeit und Wetter | `components/dashboard/hero.tsx` |
| Count-up der KPIs (nur einmal) | `components/dashboard/count-up.tsx` |

## Zustände

- **Leerzustand:** „Noch keine Anlage? Demo starten“ (`empty-state.tsx`)
- **Laden:** Skeleton statt Spinner (`ui/form.tsx → Skeleton`)
- **Fehler / veraltet:** letzter Stand mit Zeitstempel („Letzter Stand von …“), nie leer
- **Offline-Gerät:** roter Punkt und „offline seit …“

## Barrierefreiheit

- `prefers-reduced-motion` wird respektiert (Energiefluss zeigt statische Punkte, CSS-Animationen aus)
- Alle Diagramme haben `role="img"` und eine `aria-label`-Beschreibung
- Fokus sichtbar (`:focus-visible` in Amber), „Skip to content“-Link, Tastaturbedienung für Tabs
- Kontraste ≥ 4,5:1 für Text in beiden Modi

## Charts (ECharts)

- Renderer SVG, Farben ausschließlich aus `COLORS`
- Fläche nur für PV (Verlauf Amber → transparent), Verbrauch als Linie
- Prognose gestrichelt in Amber, Ladestand gepunktet auf zweiter Achse (0–100 %)
- Legende oben links, Tooltip mit Einheit (kW/kWh/ct)
