"""Render the profile cards from the public GitHub contribution calendar."""
import argparse
import base64
import calendar
from collections import defaultdict
from datetime import date, timedelta
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = "edamame69"
STATIC = os.environ.get("STATIC") == "1"
WIDTH = 896


class ContributionCalendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.counts = {}
        self.tooltip = None
        self.tooltip_parts = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "td" and {"data-date", "data-level", "id"} <= values.keys():
            self.cells[values["id"]] = (
                date.fromisoformat(values["data-date"]), int(values["data-level"])
            )
        if tag == "tool-tip":
            self.tooltip = values.get("for")
            self.tooltip_parts = []

    def handle_data(self, data):
        if self.tooltip:
            self.tooltip_parts.append(data)

    def handle_endtag(self, tag):
        if tag != "tool-tip" or self.tooltip is None:
            return
        label = "".join(self.tooltip_parts).strip()
        count = re.match(r"^(No|[0-9,]+) contributions?\b", label)
        if count:
            value = count.group(1)
            self.counts[self.tooltip] = 0 if value == "No" else int(value.replace(",", ""))
        self.tooltip = None


def read_calendar(html):
    parser = ContributionCalendar()
    parser.feed(html)
    if len(parser.cells) < 365 or not parser.cells.keys() <= parser.counts.keys():
        raise ValueError("The public GitHub calendar is incomplete or changed its markup.")
    days = sorted((day, parser.counts[key], level) for key, (day, level) in parser.cells.items())
    days = days[-365:]
    for index, (day, count, level) in enumerate(days):
        if not 0 <= level <= 4 or (count == 0) != (level == 0):
            raise ValueError(f"Invalid calendar count or level for {day}.")
        if index and day - days[index - 1][0] != timedelta(days=1):
            raise ValueError("The calendar is missing a day.")
    return days


def fetch_calendar():
    request = Request(
        f"https://github.com/users/{ACCOUNT}/contributions",
        headers={"User-Agent": "Mozilla/5.0 (compatible; GitHub profile README calendar)"},
    )
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8")


def embedded_font(family, filename):
    encoded = base64.b64encode((ROOT / "fonts" / filename).read_bytes()).decode("ascii")
    return (
        f"@font-face{{font-family:'{family}';font-display:swap;"
        f"src:url(data:font/woff2;base64,{encoded}) format('woff2')}}"
    )


STYLE = """
:root{--paper:#f8f8f3;--ink:#162344;--muted:#46597a;--line:#d9e0e9;
 --blue:#234bd7;--base:#e5eaf2;--panel:#10244b;--white:#f7faff}
@media(prefers-color-scheme:dark){
 :root{--paper:#111b2b;--ink:#f2f5ff;--muted:#bdcce8;--line:#304464;
 --blue:#9cb6ff;--base:#253754;--panel:#0a1429}
}
text{font-family:system-ui,sans-serif;fill:var(--ink)}
.serif{font-family:'Instrument Serif',Georgia,serif}
.mono{font-family:'IBM Plex Mono',monospace}
.muted{fill:var(--muted)}
.blue{fill:var(--blue)}
.white{fill:var(--white)}
.paper{fill:var(--paper);stroke:var(--line)}
.reveal{animation:rise .52s cubic-bezier(.2,.75,.25,1) both;animation-delay:var(--delay,0ms)}
.square{animation:fade .32s ease-out both;animation-delay:var(--delay,0ms)}
.bar{transform-box:fill-box;transform-origin:bottom;animation:grow .66s cubic-bezier(.2,.75,.25,1) both;
 animation-delay:var(--delay,0ms)}
.signal{stroke-dasharray:8 130;animation:travel 1.65s ease-out .34s both}
@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes grow{from{transform:scaleY(.025)}to{transform:scaleY(1)}}
@keyframes travel{from{stroke-dashoffset:138;opacity:0}20%{opacity:1}to{stroke-dashoffset:0;opacity:0}}
@media(prefers-reduced-motion:reduce){.reveal,.square,.bar,.signal{animation:none}.signal{visibility:hidden}}
"""


def label(x, y, content, size, classes="", attrs=""):
    return f'<text x="{x}" y="{y}" class="{classes}" font-size="{size}" {attrs}>{escape(str(content))}</text>'


def panel(width, height):
    return f'<rect class="paper" x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="16"/>'


def reveal(body, delay):
    return f'<g class="reveal" style="--delay:{delay}ms">{body}</g>'


def svg(width, height, title, description, body, fonts):
    css = fonts + STYLE
    if STATIC:
        css += ".reveal,.square,.bar,.signal{animation:none!important}.signal{visibility:hidden}"
    markup = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">\n'
        f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>\n'
        f'<style>{css}</style>\n{panel(width, height)}{body}\n</svg>\n'
    )
    ElementTree.fromstring(markup)
    return markup


def hero(fonts):
    body = """
    <defs>
      <pattern id="blueprint" width="13" height="13" patternUnits="userSpaceOnUse">
        <path d="M13 0H0V13" fill="none" stroke="#a4b9fb" stroke-opacity=".17"/>
      </pattern>
    </defs>
    <rect x="566" y="24" width="306" height="215" rx="11" fill="var(--panel)"/>
    <rect x="578" y="36" width="282" height="191" rx="6" fill="url(#blueprint)"/>
    <g fill="#203c78" stroke="#7695ed" stroke-width="1">
      <rect x="609" y="88" width="92" height="43" rx="6"/>
      <rect x="739" y="88" width="92" height="43" rx="6"/>
      <rect x="674" y="156" width="92" height="43" rx="6"/>
    </g>
    <g fill="none" stroke="#8da7f9" stroke-width="1.3">
      <path d="M701 109H739M785 131v13h-65v12M655 131v13h65"/>
      <path class="signal" d="M655 109H785v35h-65v12" stroke="#e6eeff" stroke-width="2"/>
    </g>
    <g fill="#a4b9fb"><circle cx="720" cy="144" r="3"/><circle cx="598" cy="57" r="3"/></g>
    """
    body += label(611, 61, "BACKEND ARCHITECTURE", 11, "mono white", 'letter-spacing="1.2"')
    for x, y, name in [(655, 113, "REST API"), (785, 113, "SERVICE"), (720, 182, "DATABASE")]:
        body += label(x, y, name, 11, "mono white", 'text-anchor="middle"')
    body += reveal(label(36, 49, "@EDAMAME69  /  HANOI", 13, "mono blue", 'letter-spacing="2"'), 0)
    body += reveal(label(33, 123, "Le Duc Minh", 81, "serif"), 85)
    body += reveal(label(37, 163, "Java backend development", 26, attrs='font-weight="650"'), 165)
    body += reveal(label(38, 202, "Information Security student at PTIT.", 19, "muted"), 225)
    body += reveal(label(38, 227, "Spring Boot, REST APIs and relational databases.", 19, "muted"), 265)
    return svg(WIDTH, 264, "Le Duc Minh", "Java backend development. Information Security student at PTIT, based in Hanoi.", body, fonts)


def heatmap(days, fonts):
    start, end = days[0][0], days[-1][0]
    first_sunday = start - timedelta(days=(start.weekday() + 1) % 7)
    total = sum(count for _, count, _ in days)
    column = 752 / (1 + (end - first_sunday).days // 7)
    colors = ["var(--base)", "#9bb4fb", "#6788f7", "#4169e4", "#234bd7"]
    body = reveal(label(34, 52, "GitHub contributions", 34, "serif"), 100)
    body += label(862, 49, f"{total:,} IN THE PAST YEAR", 13, "mono blue", 'text-anchor="end" letter-spacing="1.2"')
    for row, day_label in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        body += label(36, 108 + 14 * row, day_label, 11, "mono muted")
    last_month_x = -100
    for day, count, level in days:
        week, row = divmod((day - first_sunday).days, 7)
        x, y = 76 + week * column, 98 + row * 14
        delay = 170 + week * 9
        if (day == start or day.day == 1) and x - last_month_x >= 38 and x <= 809:
            body += label(f"{x:.2f}", 86, calendar.month_abbr[day.month], 11, "mono muted")
            last_month_x = x
        body += (
            f'<rect x="{x:.2f}" y="{y}" width="10" height="10" rx="2" fill="{colors[level]}" '
            f'class="square" style="--delay:{delay}ms"><title>{day.isoformat()}: {count}</title></rect>'
        )
    body += label(36, 223, f"{start:%d %b %Y} - {end:%d %b %Y}", 11, "mono muted")
    body += label(699, 223, "Less", 11, "mono muted")
    for index, color in enumerate(colors):
        body += f'<rect x="{735 + 15 * index}" y="214" width="10" height="10" rx="2" fill="{color}"/>'
    body += label(814, 223, "More", 11, "mono muted")
    return svg(WIDTH, 246, "GitHub contributions", f"{total} contributions across the past 365 days.", body, fonts)


def activity(days, fonts):
    monthly = defaultdict(int)
    current = longest = active = 0
    for day, count, _ in days:
        monthly[(day.year, day.month)] += count
        active += bool(count)
        current = current + 1 if count else 0
        longest = max(longest, current)
    peak_day, peak_count, _ = max(days, key=lambda entry: entry[1])
    end = days[-1][0]
    last_month = end.year * 12 + end.month - 1
    months = [(number // 12, number % 12 + 1) for number in range(last_month - 11, last_month + 1)]
    peak_month = max(months, key=lambda month: monthly[month])
    max_count = monthly[peak_month]
    body = reveal(label(34, 52, "Monthly activity", 34, "serif"), 205)
    body += label(862, 49, "LAST 12 CALENDAR MONTHS", 12, "mono blue", 'text-anchor="end" letter-spacing="1.2"')
    body += '<path d="M35 175H861M35 212H861" fill="none" stroke="var(--line)"/>'
    for index, month in enumerate(months):
        x = 48 + index * 69
        count = monthly[month]
        height = max(2, round(86 * count / max(max_count, 1)))
        highlight = month == peak_month and max_count
        color = "var(--blue)" if highlight else "#90a7e9" if count else "var(--base)"
        body += (
            f'<rect x="{x}" y="{175-height}" width="46" height="{height}" rx="4" '
            f'fill="{color}" class="bar" style="--delay:{220+index*30}ms">'
            f'<title>{calendar.month_name[month[1]]} {month[0]}: {count}</title></rect>'
        )
        body += label(x + 23, 194, calendar.month_abbr[month[1]], 11, "mono muted", 'text-anchor="middle"')
        if highlight:
            body += reveal(label(x + 23, 169 - height, count, 12, "mono blue", 'text-anchor="middle"'), 655)
    metrics = [
        (36, f"{active} active days"),
        (298, f"{longest} days longest streak"),
        (584, f"Peak day: {peak_count} on {peak_day:%d %b}" if peak_count else "No active days"),
    ]
    for x, metric in metrics:
        body += label(x, 239, metric, 14, "mono muted")
    return svg(WIDTH, 262, "Monthly activity", f"{active} active days, {longest} days longest streak, and {peak_count} contributions on the busiest day in the past year.", body, fonts)


PROJECTS = (
    ("banking", "Banking Backend", "TRANSACTION API", ("Atomic transfers", "and optimistic locking"),
     "#234bd7", "M218 38h36m-6-6 6 6-6 6m6 13h-36m6-6-6 6 6 6"),
    ("mycloud", "MyCloud", "ONGOING", ("File and folder metadata", "with per-user access"),
     "#10675c", "M216 57V37h15l5 5h21v18h-41zM224 49h24"),
    ("smartroom", "Smart Room IoT", "MQTT DASHBOARD", ("ESP8266 telemetry", "and LED controls"),
     "#a84632", "M216 57h8l6-18 7 24 6-15h15"),
)


def project_card(index, project, fonts):
    slug, title, category, lines, accent, icon = project
    body = f'<rect x="17" y="16" width="254" height="72" rx="8" fill="{accent}"/>'
    body += label(31, 58, category, 11, "mono white", 'letter-spacing="1.1"')
    body += f'<path d="{icon}" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'
    body += reveal(label(17, 129, title, 36, "serif"), 290 + index * 70)
    for y, line in zip((156, 177), lines):
        body += label(18, y, line, 15, "muted")
    body += label(18, 210, "View source", 12, "mono blue")
    body += '<path d="M247 205h20m-6-6 6 6-6 6" fill="none" stroke="var(--blue)" stroke-width="1.4"/>'
    return f"{slug}.svg", svg(288, 229, title, " ".join(lines), body, fonts)


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--calendar-html", type=Path, help="Read a saved GitHub calendar instead of fetching it.")
    args.add_argument("--output-dir", type=Path, default=ROOT, help="Write cards and data beneath this directory.")
    options = args.parse_args()
    html = options.calendar_html.read_text() if options.calendar_html else fetch_calendar()
    days = read_calendar(html)
    fonts = embedded_font("Instrument Serif", "instrument-serif.woff2")
    fonts += embedded_font("IBM Plex Mono", "ibm-plex-mono.woff2")
    cards = {"hero.svg": hero(fonts), "contributions.svg": heatmap(days, fonts), "activity.svg": activity(days, fonts)}
    cards.update(project_card(index, project, fonts) for index, project in enumerate(PROJECTS))
    cards_dir = options.output_dir / "cards"
    data_dir = options.output_dir / "data"
    cards_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    for name, markup in cards.items():
        (cards_dir / name).write_text(markup, encoding="utf-8")
    entries = [{"date": day.isoformat(), "count": count, "level": level} for day, count, level in days]
    (data_dir / "contributions.json").write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Rendered {len(cards)} cards from {len(days)} days and {sum(row[1] for row in days)} contributions.")


if __name__ == "__main__":
    main()
