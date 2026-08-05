"""
Join extracted Application Data Sheet fields (applicant/agent/architect/
owner) back onto development_applications.csv by application_number, and
report honest coverage: of the 241 development items, how many actually
have a Data Sheet, and -- more importantly -- of the subset that are
genuinely first-decision private applications (not policy reports,
by-law text amendments, area studies, or Section 37 follow-ups), what
fraction resolve. Same "don't round a partial result up" standard as
the motion-text scrape.

Output: data/processed/development_applicants.csv
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHEETS_PATH = ROOT / "data" / "interim" / "application_data_sheets.csv"
DEV_APPS_PATH = ROOT / "data" / "interim" / "development_applications.csv"
AGENDA_ITEMS_PATH = ROOT / "data" / "interim" / "agenda_items.csv"
OUT_PATH = ROOT / "data" / "processed" / "development_applicants.csv"


def normalize_app_number(s):
    return " ".join(s.split()).strip().upper()


def main():
    with SHEETS_PATH.open("r", newline="", encoding="utf-8") as f:
        sheets = list(csv.DictReader(f))
    with DEV_APPS_PATH.open("r", newline="", encoding="utf-8") as f:
        dev_apps = list(csv.DictReader(f))
    with AGENDA_ITEMS_PATH.open("r", newline="", encoding="utf-8") as f:
        agenda_items = {r["agenda_item_id"]: r for r in csv.DictReader(f)}

    dev_apps_by_number = {}
    for r in dev_apps:
        key = normalize_app_number(r["application_number"])
        dev_apps_by_number.setdefault(key, []).append(r)

    out_rows = []
    matched_to_dev_apps = 0
    for r in sheets:
        item = agenda_items.get(r["item_id"], {})
        row = {
            "item_id": r["item_id"],
            "agenda_item_title": item.get("agenda_item_title", ""),
            "found_data_sheet": r["found"],
            "application_number": r["application_number"],
            "applicant": r["applicant"],
            "agent": r["agent"],
            "architect": r["architect"],
            "owner": r["owner"],
            "matched_dev_applications_row": False,
            "dev_app_street": "",
        }
        if r["found"] == "True" and r["application_number"]:
            key = normalize_app_number(r["application_number"])
            candidates = dev_apps_by_number.get(key, [])
            if candidates:
                row["matched_dev_applications_row"] = True
                row["dev_app_street"] = f"{candidates[0]['street_num']} {candidates[0]['street_name']} {candidates[0]['street_type']}".strip()
                matched_to_dev_apps += 1
        out_rows.append(row)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    n_found = sum(1 for r in out_rows if r["found_data_sheet"] == "True")
    n_total = len(out_rows)

    # Heuristic for "genuinely a first-decision application" vs. policy/
    # report/by-law/study/follow-up items, based on title keywords --
    # mirrors the same "don't force 100%, explain the gap" approach used
    # for the motion-text scrape.
    NON_APPLICATION_KEYWORDS = [
        "annual progress report", "municipal code", "secondary plan",
        "authority to amend section 37", "monitoring", "work plan",
        "status report", "policy review", "action plan",
    ]

    def looks_like_non_application(title):
        t = title.lower()
        return any(k in t for k in NON_APPLICATION_KEYWORDS)

    likely_non_application = [r for r in out_rows if looks_like_non_application(r["agenda_item_title"])]
    likely_application = [r for r in out_rows if not looks_like_non_application(r["agenda_item_title"])]
    found_among_likely_application = sum(1 for r in likely_application if r["found_data_sheet"] == "True")

    print(f"Data Sheet found: {n_found} of {n_total} items ({100 * n_found / n_total:.1f}%)")
    print(f"Application_number extracted and matched back to development_applications.csv: {matched_to_dev_apps}")
    print()
    print(f"Items whose title suggests policy/report/by-law/study/follow-up (not a private application): {len(likely_non_application)}")
    print(f"Items that look like an actual application decision: {len(likely_application)}")
    print(f"  Data Sheet found among those: {found_among_likely_application} of {len(likely_application)} "
          f"({100 * found_among_likely_application / len(likely_application):.1f}%)")
    print(f"-> {OUT_PATH}")


if __name__ == "__main__":
    main()
