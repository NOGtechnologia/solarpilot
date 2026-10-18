"""Monatsreport: Ertrag, Ersparnis, vermiedenes CO₂, Vergleich zum Vorjahr – als JSON und PDF."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fpdf import FPDF
from sqlmodel import Session

from app.models import Site

from .stats import energy_history

MONTHS_DE = [
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
]
MONTHS_EN = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def month_days(year: int, month: int) -> list[date]:
    first = date(year, month, 1)
    nxt = (first + timedelta(days=32)).replace(day=1)
    return [first + timedelta(days=i) for i in range((nxt - first).days)]


def monthly_report(
    session: Session, sites: list[Site], year: int, month: int, today: date | None = None
) -> dict[str, Any]:
    cur = energy_history(session, sites, month_days(year, month))
    prev_days = month_days(year - 1, month)
    today = today or date.today()
    if (year, month) == (today.year, today.month):
        # laufender Monat: nur mit denselben Tagen des Vorjahres vergleichen
        prev_days = [d for d in prev_days if d.day <= today.day]
    prev = energy_history(session, sites, prev_days)
    total, prev_total = cur["total"], prev["total"]
    best_idx = (
        max(range(len(cur["pv_kwh"])), key=lambda i: cur["pv_kwh"][i]) if cur["pv_kwh"] else None
    )
    change = None
    if prev_total["pv_wh"] > 0:
        change = round((total["pv_wh"] - prev_total["pv_wh"]) / prev_total["pv_wh"] * 100, 1)
    return {
        "year": year,
        "month": month,
        "sites": [s.name for s in sites],
        "total": total,
        "previous_year": prev_total,
        "change_pct": change,
        "best_day": {"day": cur["labels"][best_idx], "pv_kwh": cur["pv_kwh"][best_idx]}
        if best_idx is not None and cur["pv_kwh"][best_idx] > 0
        else None,
        "days": cur,
    }


def _txt(s: str) -> str:
    # Kernschriften von fpdf sind Latin-1
    return (
        s.replace("€", "EUR")
        .replace("₂", "2")
        .replace("–", "-")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


def report_pdf(report: dict[str, Any], lang: str = "de") -> bytes:
    de = lang == "de"
    months = MONTHS_DE if de else MONTHS_EN
    t = report["total"]
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_fill_color(245, 165, 36)
    pdf.rect(0, 0, 210, 28, "F")
    pdf.set_text_color(11, 15, 20)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_xy(12, 8)
    title = "SolarPilot Monatsreport" if de else "SolarPilot monthly report"
    pdf.cell(0, 12, _txt(f"{title} - {months[report['month'] - 1]} {report['year']}"))
    pdf.set_text_color(30, 30, 30)
    pdf.set_xy(12, 34)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _txt(("Anlagen: " if de else "Sites: ") + ", ".join(report["sites"])))
    pdf.ln(10)

    def kv(label: str, value: str) -> None:
        pdf.set_x(12)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(80, 8, _txt(label))
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, _txt(value), new_x="LMARGIN", new_y="NEXT")

    def pct(v: float | None) -> str:
        return "-" if v is None else f"{v:.0f} %"

    kv("Ertrag" if de else "Yield", f"{t['pv_wh'] / 1000:.1f} kWh")
    kv("Verbrauch" if de else "Consumption", f"{t['load_wh'] / 1000:.1f} kWh")
    kv("Netzbezug" if de else "Grid import", f"{t['import_wh'] / 1000:.1f} kWh")
    kv("Einspeisung" if de else "Feed-in", f"{t['export_wh'] / 1000:.1f} kWh")
    kv("Eigenverbrauchsquote" if de else "Self-consumption", pct(t["self_consumption_pct"]))
    kv("Autarkie" if de else "Self-sufficiency", pct(t["autarky_pct"]))
    kv("Ersparnis" if de else "Savings", f"{t['savings_eur']:.2f} EUR")
    kv("CO2 vermieden" if de else "CO2 avoided", f"{t['co2_kg']:.0f} kg")
    if report["change_pct"] is not None:
        kv("Vergleich Vorjahr" if de else "vs. previous year", f"{report['change_pct']:+.1f} %")
    if report["best_day"]:
        kv(
            "Bester Tag" if de else "Best day",
            f"{report['best_day']['day']} ({report['best_day']['pv_kwh']:.1f} kWh)",
        )

    # Balkendiagramm Tagesertrag
    days = report["days"]
    vals = days["pv_kwh"]
    pdf.ln(6)
    pdf.set_x(12)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(
        0,
        8,
        _txt("Tagesertrag (kWh)" if de else "Daily yield (kWh)"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    top = pdf.get_y() + 2
    height, left, width = 60, 14, 182
    vmax = max(vals + [0.1])
    bw = width / max(len(vals), 1)
    pdf.set_draw_color(220, 220, 220)
    pdf.line(left, top + height, left + width, top + height)
    pdf.set_fill_color(245, 165, 36)
    for i, v in enumerate(vals):
        h = height * (v / vmax)
        if h > 0:
            pdf.rect(left + i * bw + bw * 0.15, top + height - h, bw * 0.7, h, "F")
    pdf.set_font("Helvetica", "", 7)
    for i in range(0, len(vals), 5):
        pdf.set_xy(left + i * bw, top + height + 1)
        pdf.cell(bw * 2, 4, str(i + 1))
    pdf.set_xy(left, top - 1)
    pdf.cell(20, 4, f"{vmax:.0f}")
    pdf.set_y(top + height + 12)
    pdf.set_x(12)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(
        0,
        4,
        _txt(
            "Ersparnis = Eigenverbrauch x Strompreis + Einspeisung x Vergütung. "
            "CO2 nach Faktor aus den Einstellungen."
            if de
            else "Savings = self-consumption x price + feed-in x tariff. CO2 factor from settings."
        ),
    )
    return bytes(pdf.output())
