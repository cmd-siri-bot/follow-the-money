"""
Download and parse the "Application Data Sheet" attachment for all 241
development items, per docs/08-decision-log.md's staff-report-PDF-route
scoping. For each item, tries its linked background-info PDFs in
ascending file-number order (earliest report first) and stops at the
first one containing a Data Sheet -- matches the sample-run approach
that found the primary decision report (not later supplementary
reports) carries this attachment.

Population note, stated up front (same honesty standard as the motion-
text scrape): not every one of the 241 items is a decision on a private
application -- some are policy reports, by-law text amendments, area
secondary-plan studies, or Section 37 follow-ups with no Data Sheet to
find. The sample run (12 items) found 8/12 hits, with the 4 misses all
explained by item type, not scraper failure.

Inputs:
  data/raw/dev_application_bgrd_links/all_bgrd_links.json -- {item_id: [pdf_url, ...]}
Outputs:
  data/raw/dev_application_pdfs/*.pdf -- downloaded reports (gitignored, local only)
  data/interim/application_data_sheets.csv -- one row per item: item_id, found,
    matched_url, matched_page, applicant, agent, architect, owner, application_number
"""
import csv
import json
import re
import sys
import urllib.request
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_application_data_sheet import find_and_parse_data_sheet  # noqa: E402

LINKS_PATH = ROOT / "data" / "raw" / "dev_application_bgrd_links" / "all_bgrd_links.json"
PDF_DIR = ROOT / "data" / "raw" / "dev_application_pdfs"
OUT_PATH = ROOT / "data" / "interim" / "application_data_sheets.csv"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
APP_NUMBER_RE = re.compile(r"Application Number:\s*([0-9A-Za-z .;]+?)(?:\n|Application Type:|Project Description:|$)")


def download(url, dest):
    if dest.exists():
        return
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=45) as resp:
        dest.write_bytes(resp.read())


def extract_application_number(page_text):
    m = APP_NUMBER_RE.search(page_text)
    return m.group(1).strip() if m else ""


def main():
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    links_by_item = json.loads(LINKS_PATH.read_text(encoding="utf-8"))

    rows = []
    n_downloaded = 0
    for i, (item_id, urls) in enumerate(sorted(links_by_item.items())):
        found = None
        for url in urls:
            fname = url.rsplit("/", 1)[-1]
            dest = PDF_DIR / f"{item_id.replace('.', '_')}__{fname}"
            if not dest.exists():
                try:
                    download(url, dest)
                    n_downloaded += 1
                except Exception as e:  # noqa: BLE001
                    print(f"  [{item_id}] download failed for {url}: {e}")
                    continue
            try:
                with pdfplumber.open(dest) as pdf:
                    result = find_and_parse_data_sheet(pdf)
                    if result:
                        page_num, fields = result
                        app_number = extract_application_number(pdf.pages[page_num - 1].extract_text() or "")
            except Exception as e:  # noqa: BLE001
                print(f"  [{item_id}] parse failed for {dest.name}: {e}")
                continue
            if result:
                found = (url, page_num, fields, app_number)
                break

        if found:
            url, page_num, fields, app_number = found
            rows.append({
                "item_id": item_id,
                "found": True,
                "matched_url": url,
                "matched_page": page_num,
                "application_number": app_number,
                "applicant": fields.get("Applicant", ""),
                "agent": fields.get("Agent", ""),
                "architect": fields.get("Architect", ""),
                "owner": fields.get("Owner", ""),
            })
        else:
            rows.append({
                "item_id": item_id, "found": False, "matched_url": "", "matched_page": "",
                "application_number": "", "applicant": "", "agent": "", "architect": "", "owner": "",
            })

        if (i + 1) % 20 == 0:
            print(f"  ...{i + 1}/{len(links_by_item)} items processed ({n_downloaded} PDFs downloaded so far)")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    n_found = sum(1 for r in rows if r["found"])
    print(f"\nData Sheet found for {n_found} of {len(rows)} items ({100 * n_found / len(rows):.1f}%)")
    print(f"Total PDFs downloaded this run: {n_downloaded}")
    print(f"-> {OUT_PATH}")


if __name__ == "__main__":
    main()
