"""City of Toronto Council/Committee agenda scraper (TMMIS), shared by
TorontoSpends -- see apps/council.

secure.toronto.ca is behind Akamai bot management: plain HTTP clients
(requests, curl) get 403 Access Denied even with full browser headers,
and so does a *headless* Chromium via Playwright. Only a real,
non-headless browser session gets through (verified 2026-08-06). That
means ingestion here is a manual/offline step -- see
requirements-scraping.txt -- not something that runs inside the live
Django web app.

Meeting enumeration doesn't need scraping at all: the City's own open
data has a clean "meeting-schedule-all-committees-2022-2026" CKAN
resource giving every meeting (body, date, meeting number) for the
current council term. Only the actual item content requires the
browser-based scrape.
"""
import re
import time
from datetime import date, datetime

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from common.ckan_client import fetch_resource

# open.toronto.ca dataset "city-council-and-committees-meeting-schedule-reports",
# resource "meeting-schedule-all-committees-2022-2026" (datastore-enabled CSV).
MEETING_SCHEDULE_RESOURCE_ID = "08c8aedb-afba-41f5-830e-bbfb305ebbc7"

# Hand-verified against real secure.toronto.ca URLs, not guessed -- each
# code was confirmed live (2026-08-06) by fetching a recent real meeting
# for that body and checking the committee's own name appears on the
# returned page. Extend only after verifying a body's code the same way
# -- a wrong code silently produces a 404/empty scrape, not an error.
#
# Scope: City Council + its standing/special committees + the 4
# Community Councils, per the project's approved plan. Excludes agency
# boards (TTC, Police Services Board, Library Board, Board of Health,
# CreateTO, Exhibition Place -- same category, just not literally named
# in the original exclusion list) and advisory/nominating/quasi-judicial
# bodies (e.g. Sign Variance Committee, Dangerous Dog Review Tribunal,
# various Advisory Committees and Nominating Panels) -- those aren't
# part of the core legislative decision chain this feature answers
# "what's the status of X" against.
COMMITTEE_CODES = {
    "City Council": "CC",
    "Executive Committee": "EX",
    "Planning and Housing Committee": "PH",
    "Economic and Community Development Committee": "EC",
    "Infrastructure and Environment Committee": "IE",
    "General Government Committee": "GG",
    "Budget Committee": "BU",
    "Audit Committee": "AU",
    "Civic Appointments Committee": "CA",
    "Etobicoke York Community Council": "EY",
    "North York Community Council": "NY",
    "Scarborough Community Council": "SC",
    "Toronto and East York Community Council": "TE",
}

REQUEST_DELAY_SECONDS = 1.0
ITEM_HEADING_RE = re.compile(r"^([A-Z]{2,3}\d+\.\d+)\s*-\s*(.+)$")


def fetch_meeting_schedule(committees: list[str], since: date) -> list[dict]:
    """Every scheduled meeting for the given committee names (must match
    the open-data 'Committee' field exactly) on/after `since`. Returns
    dicts with committee/mtg_number/date -- callers turn these into
    TMMIS meeting IDs via tmmis_meeting_id()."""
    rows = fetch_resource(MEETING_SCHEDULE_RESOURCE_ID)
    out = []
    for r in rows:
        if r.get("Committee") not in committees:
            continue
        raw_date = r.get("Date")
        if not raw_date:
            continue
        d = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()
        if d < since:
            continue
        out.append({"committee": r["Committee"], "mtg_number": r["MTG #"], "date": d})
    return out


def tmmis_meeting_id(committee: str, mtg_number: str, meeting_date: date) -> str | None:
    code = COMMITTEE_CODES.get(committee)
    if not code:
        return None
    return f"{meeting_date.year}.{code}{mtg_number}"


def _clean(el) -> str:
    return el.get_text(" ", strip=True)


class AgendaScraper:
    """One real (non-headless) browser session, reused across many page
    fetches -- launching a fresh browser per page would be far slower.
    Use as a context manager:

        with AgendaScraper() as scraper:
            items = scraper.fetch_meeting_item_ids("2025.EX20")
            for item_id, _title in items:
                record = scraper.fetch_agenda_item(item_id)
    """

    def __init__(self, delay: float = REQUEST_DELAY_SECONDS):
        self.delay = delay
        self._pw = None
        self._browser = None
        self._page = None

    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=False)
        self._page = self._browser.new_page()
        return self

    def __exit__(self, *exc):
        self._browser.close()
        self._pw.stop()

    def _get_html(self, url: str) -> str:
        self._page.goto(url, timeout=30000)
        html = self._page.content()
        time.sleep(self.delay)
        return html

    def fetch_meeting_item_ids(self, meeting_id: str) -> list[tuple[str, str]]:
        """[(item_id, title), ...] listed on a meeting's agenda page.
        Item headings are "<h3>{CODE}.{N} - {Title}</h3>" -- CODE.N
        (e.g. "EX20.12") is prefixed with the meeting's year to form the
        full item_id used everywhere else ("2025.EX20.12")."""
        url = f"https://secure.toronto.ca/council/report.do?meeting={meeting_id}&type=agenda"
        html = self._get_html(url)
        soup = BeautifulSoup(html, "lxml")
        year = meeting_id.split(".")[0]
        items = []
        for h3 in soup.find_all("h3"):
            m = ITEM_HEADING_RE.match(_clean(h3))
            if m:
                code, title = m.groups()
                items.append((f"{year}.{code}", title))
        return items

    def fetch_agenda_item(self, item_id: str) -> dict:
        """Full consolidated item-history page for one item_id, per
        apps/council/models.py::AgendaItem's field set."""
        url = f"https://secure.toronto.ca/council/agenda-item.do?item={item_id}"
        html = self._get_html(url)
        soup = BeautifulSoup(html, "lxml")

        h3 = soup.find("h3")
        title = ""
        if h3:
            m = ITEM_HEADING_RE.match(_clean(h3))
            title = m.group(2) if m else _clean(h3)

        def dt_dd(label):
            dt = soup.find("dt", string=re.compile(rf"^\s*{re.escape(label)}:?\s*$"))
            if dt:
                dd = dt.find_next_sibling("dd")
                if dd:
                    return _clean(dd)
            return ""

        tracking_status_text = ""
        h2 = soup.find("h2", string=re.compile(r"Tracking Status"))
        if h2:
            ul = h2.find_next("ul")
            if ul:
                tracking_status_text = " ".join(_clean(li) for li in ul.find_all("li"))

        def section_text(*labels):
            # Document-order walk rather than strict siblings -- the page's
            # accordion wrapper divs mean content isn't always a direct
            # sibling of its <h4> heading.
            for label in labels:
                h4 = soup.find("h4", string=re.compile(rf"^\s*{re.escape(label)}\s*$"))
                if not h4:
                    continue
                parts = []
                for el in h4.find_all_next():
                    if el.name in ("h3", "h4"):
                        break
                    if el.name in ("p", "li"):
                        t = _clean(el)
                        if t:
                            parts.append(t)
                text = " ".join(parts)
                if text:
                    return text
            return ""

        background_docs = []
        bg_h4 = soup.find("h4", string=re.compile(r"^\s*Background Information\s*$"))
        if bg_h4:
            for el in bg_h4.find_all_next():
                if el.name in ("h3", "h4"):
                    break
                if el.name == "a" and el.get("href", "").lower().endswith(".pdf"):
                    background_docs.append({"title": _clean(el), "pdf_url": el["href"]})

        return {
            "item_id": item_id,
            "title": title,
            "consideration_type": dt_dd("Decision Type"),
            "status_text": dt_dd("Status"),
            "wards": dt_dd("Wards"),
            "tracking_status_text": tracking_status_text,
            "origin_text": section_text("Origin"),
            "summary_text": section_text("Summary"),
            "decision_text": section_text("City Council Decision", "Committee Decision", "Committee Recommendations"),
            "background_documents": background_docs,
            "source_url": url,
        }
