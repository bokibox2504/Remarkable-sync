#!/usr/bin/env python3
"""
Generates a daily/weekly PDF schedule from a Google Calendar secret ICS feed,
optimized for reMarkable Paper Pro Move (portrait, large readable text).
Color-codes events by keyword, matching the user's Google Calendar scheme:
11=red/urgent, 9=blue/deep work, 6=orange/admin, 2=green/personal, 8=graphite/buffer.

Reads:
  ICS_URL       - Google Calendar "Secret address in iCal format"
  DAYS_AHEAD    - how many days to include (default 7)
  TIMEZONE      - IANA timezone (default Europe/Belgrade)

Writes:
  output/raspored.pdf
"""

import os
import sys
import requests
from datetime import datetime, timedelta
from icalendar import Calendar
import pytz
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors

ICS_URL = os.environ.get("ICS_URL")
DAYS_AHEAD = int(os.environ.get("DAYS_AHEAD", "7"))
TZ_NAME = os.environ.get("TIMEZONE", "Europe/Belgrade")
TZ = pytz.timezone(TZ_NAME)

PAGE_WIDTH = 130 * mm
PAGE_HEIGHT = 180 * mm

RED = colors.HexColor("#D50000")       # urgent
BLUE = colors.HexColor("#3F51B5")      # deep work
ORANGE = colors.HexColor("#FF9800")    # admin
GREEN = colors.HexColor("#4CAF50")     # personal
GRAPHITE = colors.HexColor("#757575")  # buffer
BLACK = colors.HexColor("#212121")

# Keyword -> color. Checked in order; first match wins. Case-insensitive, matches Serbian/Bosnian text.
KEYWORD_RULES = [
    (["hitno", "urgent", "rok", "krajnji"], RED),
    (["poziv", "sastanak", "dogovor", "ministarstvo", "savez", "tsrs",
      "elektrokrajina", "elektro", "kontakt", "administracija", "dokument",
      "izvjestaj", "izvještaj", "prijava"], ORANGE),
    (["priprema", "pisanje", "analiza", "plan rada", "raspored", "montaza",
      "montaža", "snimanje", "emisija"], BLUE),
    (["trening", "padel", "teren", "licno", "lično", "porodica", "rucak",
      "ručak", "odmor"], GREEN),
    (["pauza", "putovanje", "prevoz", "buffer", "cekanje", "čekanje"], GRAPHITE),
]


def classify_color(title):
    t = title.lower()
    for keywords, color in KEYWORD_RULES:
        for kw in keywords:
            if kw in t:
                return color
    return BLACK


def fetch_events():
    if not ICS_URL:
        print("ERROR: ICS_URL environment variable not set", file=sys.stderr)
        sys.exit(1)

    resp = requests.get(ICS_URL, timeout=30)
    resp.raise_for_status()
    cal = Calendar.from_ical(resp.content)

    now = datetime.now(TZ)
    start_range = TZ.localize(datetime(now.year, now.month, now.day))
    end_range = start_range + timedelta(days=DAYS_AHEAD)

    events = []
    for component in cal.walk("VEVENT"):
        dtstart = component.get("dtstart").dt
        summary = str(component.get("summary", "Bez naziva"))
        location = str(component.get("location", "") or "")

        if isinstance(dtstart, datetime):
            if dtstart.tzinfo is None:
                dtstart = TZ.localize(dtstart)
            else:
                dtstart = dtstart.astimezone(TZ)
            all_day = False
        else:
            dtstart = TZ.localize(datetime(dtstart.year, dtstart.month, dtstart.day))
            all_day = True

        if start_range <= dtstart < end_range:
            events.append({
                "start": dtstart,
                "summary": summary,
                "location": location,
                "all_day": all_day,
                "color": classify_color(summary),
            })

    events.sort(key=lambda e: e["start"])
    return events, start_range


def group_by_day(events, start_range, days):
    grouped = {}
    for i in range(days):
        day = start_range + timedelta(days=i)
        grouped[day.date()] = []
    for e in events:
        d = e["start"].date()
        if d in grouped:
            grouped[d].append(e)
    return grouped


DAY_NAMES = ["Ponedjeljak", "Utorak", "Srijeda", "Četvrtak", "Petak", "Subota", "Nedjelja"]
MONTH_NAMES = ["januar", "februar", "mart", "april", "maj", "jun",
               "jul", "avgust", "septembar", "oktobar", "novembar", "decembar"]


def draw_day_page(c, day_date, day_events):
    c.setFont("Helvetica-Bold", 16)
    day_name = DAY_NAMES[day_date.weekday()]
    header = f"{day_name}, {day_date.day}. {MONTH_NAMES[day_date.month - 1]} {day_date.year}."
    c.drawString(10 * mm, PAGE_HEIGHT - 15 * mm, header)

    c.setLineWidth(0.5)
    c.line(10 * mm, PAGE_HEIGHT - 18 * mm, PAGE_WIDTH - 10 * mm, PAGE_HEIGHT - 18 * mm)

    y = PAGE_HEIGHT - 26 * mm
    if not day_events:
        c.setFont("Helvetica-Oblique", 11)
        c.setFillColor(colors.grey)
        c.drawString(12 * mm, y, "Nema zakazanih događaja.")
    else:
        for e in day_events:
            time_str = "Cijeli dan" if e["all_day"] else e["start"].strftime("%H:%M")

            c.setFillColor(e["color"])
            c.rect(10 * mm, y - 1 * mm, 1.5 * mm, 5.5 * mm, fill=1, stroke=0)

            c.setFont("Helvetica-Bold", 11)
            c.setFillColor(colors.black)
            c.drawString(14 * mm, y, time_str)

            c.setFont("Helvetica", 11)
            title = e["summary"]
            if len(title) > 38:
                title = title[:35] + "..."
            c.drawString(34 * mm, y, title)

            if e["location"]:
                y -= 5 * mm
                c.setFont("Helvetica-Oblique", 9)
                c.setFillColor(colors.grey)
                loc = e["location"]
                if len(loc) > 45:
                    loc = loc[:42] + "..."
                c.drawString(34 * mm, y, f"Lokacija: {loc}")

            y -= 9 * mm
            if y < 15 * mm:
                break

    c.showPage()


def main():
    events, start_range = fetch_events()
    grouped = group_by_day(events, start_range, DAYS_AHEAD)

    os.makedirs("output", exist_ok=True)
    out_path = "output/raspored.pdf"
    c = canvas.Canvas(out_path, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))

    for day_date, day_events in grouped.items():
        draw_day_page(c, day_date, day_events)

    c.save()
    print(f"OK: generated {out_path} with {len(events)} events across {DAYS_AHEAD} days")


if __name__ == "__main__":
    main()
