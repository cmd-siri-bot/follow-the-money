"""Import City Council/Committee agenda items into apps.council.

Unlike apps/lobbying and apps/grants (infrequent full-file re-pulls,
wipe-and-reload), this ingests a continuously-growing dataset and is
meant to be re-run repeatedly, so it upserts by item_id rather than
deleting everything first -- see apps/council/models.py's AgendaItem
docstring.

Manual/offline command -- requires requirements-scraping.txt (Playwright
+ real, non-headless Chromium; secure.toronto.ca blocks plain HTTP
clients and even headless browsers, verified 2026-08-06). Run with:

    python manage.py import_council_agendas --committees "Executive Committee" --since 2024-01-01

A visible browser window will open and drive itself -- don't close it
while the command runs.
"""
import os
import sys
from datetime import date, datetime

# Playwright's sync API leaves an event-loop marker that trips Django's
# async-safety check on ORM calls made afterward in the same process --
# a known interaction, not a real async-context bug. Must be set before
# any Django DB access happens.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

sys.path.insert(0, str(settings.BASE_DIR.parent))
from common.toronto_agenda_client import (  # noqa: E402
    AgendaScraper,
    COMMITTEE_CODES,
    fetch_meeting_schedule,
    tmmis_meeting_id,
)

from apps.council.models import AgendaItem, BackgroundDocument, Meeting

BODY_TYPE_BY_COMMITTEE = {
    "City Council": Meeting.COUNCIL,
    "Executive Committee": Meeting.STANDING_COMMITTEE,
}

STATUS_MAP = [
    # (substring found in tracking_status_text/status_text, AgendaItem.status value)
    # Order matters -- checked top to bottom, first match wins.
    ("indefinitely suspend", AgendaItem.NOT_ADOPTED),
    ("not adopted", AgendaItem.NOT_ADOPTED),
    ("deferred", AgendaItem.DEFERRED),
    ("referred", AgendaItem.REFERRED),
    ("received", AgendaItem.RECEIVED),
    ("amended", AgendaItem.AMENDED),
    ("adopted", AgendaItem.ADOPTED),
]


def _classify_status(record: dict) -> str:
    haystack = f"{record.get('status_text', '')} {record.get('tracking_status_text', '')} {record.get('decision_text', '')}".lower()
    for needle, status in STATUS_MAP:
        if needle in haystack:
            return status
    return AgendaItem.UNKNOWN


def _last_considered_date(tracking_status_text: str) -> date | None:
    # Tracking status text is a run of sentences like "...on February 5, 2025...".
    # Pull the last "Month D, YYYY" found -- it's the most recent action.
    import re
    matches = re.findall(
        r"(January|February|March|April|May|June|July|August|September|October|November|December) (\d{1,2}), (\d{4})",
        tracking_status_text,
    )
    if not matches:
        return None
    month, day, year = matches[-1]
    return datetime.strptime(f"{month} {day} {year}", "%B %d %Y").date()


class Command(BaseCommand):
    help = "Scrape City Council/Committee agenda items into apps.council (manual/offline, needs a real browser)."

    def add_arguments(self, parser):
        parser.add_argument("--committees", nargs="+", default=list(COMMITTEE_CODES.keys()))
        parser.add_argument("--since", default="2022-11-01", help="YYYY-MM-DD, meetings on/after this date")

    def handle(self, *args, **options):
        committees = options["committees"]
        since = datetime.strptime(options["since"], "%Y-%m-%d").date()
        retrieved_at = timezone.now()

        for c in committees:
            if c not in COMMITTEE_CODES:
                self.stderr.write(self.style.ERROR(f"Unknown committee code for {c!r} -- add it to COMMITTEE_CODES first, don't guess."))
                return

        schedule = fetch_meeting_schedule(committees, since=since)
        # Dedupe multi-day meetings (same committee+mtg_number spanning >1 calendar date)
        seen_meetings = {}
        for row in schedule:
            mid = tmmis_meeting_id(row["committee"], row["mtg_number"], row["date"])
            if mid and mid not in seen_meetings:
                seen_meetings[mid] = row

        self.stdout.write(f"{len(seen_meetings)} meetings to scan across {committees} since {since}.")

        items_seen = 0
        items_written = 0
        with AgendaScraper() as scraper:
            for meeting_id, row in seen_meetings.items():
                meeting, _ = Meeting.objects.update_or_create(
                    tmmis_meeting_id=meeting_id,
                    defaults={
                        "body_type": BODY_TYPE_BY_COMMITTEE.get(row["committee"], Meeting.SPECIAL),
                        "body_name": row["committee"],
                        "meeting_number": int(row["mtg_number"]) if str(row["mtg_number"]).isdigit() else None,
                        "meeting_date": row["date"],
                        "source_url": f"https://secure.toronto.ca/council/report.do?meeting={meeting_id}&type=agenda",
                        "retrieved_at": retrieved_at,
                    },
                )
                try:
                    item_stubs = scraper.fetch_meeting_item_ids(meeting_id)
                except Exception as e:
                    self.stderr.write(self.style.WARNING(f"Skipping {meeting_id}: couldn't fetch agenda page ({e})"))
                    continue

                for item_id, _title in item_stubs:
                    items_seen += 1
                    try:
                        record = scraper.fetch_agenda_item(item_id)
                    except Exception as e:
                        self.stderr.write(self.style.WARNING(f"Skipping item {item_id}: {e}"))
                        continue

                    status = _classify_status(record)
                    last_date = _last_considered_date(record["tracking_status_text"]) or row["date"]

                    item, _ = AgendaItem.objects.update_or_create(
                        item_id=record["item_id"],
                        defaults={
                            "title": record["title"][:500],
                            "primary_meeting": meeting,
                            "consideration_type": record["consideration_type"][:200],
                            "wards": record["wards"][:1000],
                            "origin_text": record["origin_text"],
                            "summary_text": record["summary_text"],
                            "decision_text": record["decision_text"],
                            "tracking_status_text": record["tracking_status_text"],
                            "status": status,
                            "last_considered_date": last_date,
                            "source_url": record["source_url"],
                            "retrieved_at": retrieved_at,
                        },
                    )
                    items_written += 1

                    BackgroundDocument.objects.filter(item=item).delete()
                    for doc in record["background_documents"]:
                        BackgroundDocument.objects.create(item=item, title=doc["title"], pdf_url=doc["pdf_url"])

                self.stdout.write(f"  {meeting_id}: {len(item_stubs)} items ({items_written}/{items_seen} written so far)")

        self.stdout.write(self.style.SUCCESS(f"Done. {items_written} agenda items written from {len(seen_meetings)} meetings."))
