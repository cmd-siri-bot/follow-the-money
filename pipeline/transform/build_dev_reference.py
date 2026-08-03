"""
Build a development-sector reference table for Signal 3 (name matching)
per docs/02-donor-classification.md.

docs/02 assumed a reference list buildable from three sources: Ontario
Business Registry directorships, lobbyist registry filings, and development
application applicant names. Per docs/08-decision-log.md (2026-08-02, "Two
docs/02 assumptions don't hold against the real interim data"), the
development_applications.csv extract has no applicant/developer name field
(only a City of Toronto staff contact), and Ontario Business Registry was
never pulled. **This reference list is built from the lobbyist registry
alone.**

Precision over recall (per docs/02: "a false positive here is a harm to a
real person"). Two deliberate restrictions:

1. Only `registrant_Type == "In-house"` lobbyists are treated as officers/
   employees of the firm they represent. "Consultant" type registrants
   lobby on behalf of a client -- they are not that client's officer, and
   including them would mean flagging a donor as "development-affiliated"
   because they share a name with someone who was once *hired by* a
   developer, which is a much weaker and more defamation-prone claim.
2. Only subject matters whose `SubjectMatter` text mentions development,
   planning, zoning, or land use are included -- an in-house lobbyist for a
   grocery chain lobbying about parking bylaws is not a development-sector
   signal.

Output: data/interim/dev_sector_reference.csv
  match_key       -- normalized "last, first" for exact-ish matching against
                      donor match_key (see normalize_names.py)
  name_raw, name_last, name_first
  position_title
  firm_name        -- the beneficiary/client name tied to this registrant's
                      subject matter filing (may be blank)
  subject_matter_number, subject_matter_text
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from normalize_names import normalize_name  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SUBJ_PATH = ROOT / "data" / "interim" / "lobbyist_subject_matters.csv"
BENE_PATH = ROOT / "data" / "interim" / "lobbyist_beneficiaries.csv"
OUT_PATH = ROOT / "data" / "interim" / "dev_sector_reference.csv"

DEV_KEYWORDS = ["Development", "Planning", "Zoning", "Land Use"]


def is_dev_related(subject_matter_text: str) -> bool:
    text = (subject_matter_text or "").lower()
    return any(kw.lower() in text for kw in DEV_KEYWORDS)


def main():
    with SUBJ_PATH.open("r", newline="", encoding="utf-8") as f:
        subj_rows = list(csv.DictReader(f))

    with BENE_PATH.open("r", newline="", encoding="utf-8") as f:
        bene_rows = list(csv.DictReader(f))

    # First beneficiary/client name per subject_matter_number (there can be
    # several -- parent companies, coalition members, etc. Take the first
    # "Client" type if present, else the first row, for a single display name.
    firm_by_sm = {}
    for r in bene_rows:
        sm = r["subject_matter_number"]
        if sm not in firm_by_sm or r.get("Type") == "Client":
            firm_by_sm[sm] = r.get("Name", "")

    seen = set()
    out_rows = []
    skipped_not_dev = 0
    skipped_not_inhouse = 0
    skipped_no_name = 0

    for r in subj_rows:
        if not is_dev_related(r.get("SubjectMatter", "")):
            skipped_not_dev += 1
            continue
        if r.get("registrant_Type") != "In-house":
            skipped_not_inhouse += 1
            continue

        last = (r.get("registrant_LastName") or "").strip()
        first = (r.get("registrant_FirstName") or "").strip()
        if not last or not first:
            skipped_no_name += 1
            continue

        norm = normalize_name(f"{last}, {first}")
        dedupe_key = (norm["match_key"], r["SMNumber"])
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        out_rows.append({
            "match_key": norm["match_key"],
            "name_raw": f"{last}, {first}",
            "name_last": last,
            "name_first": first,
            "position_title": r.get("registrant_PositionTitle", ""),
            "firm_name": firm_by_sm.get(r["SMNumber"], ""),
            "subject_matter_number": r["SMNumber"],
            "subject_matter_text": r.get("SubjectMatter", ""),
        })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "match_key", "name_raw", "name_last", "name_first",
            "position_title", "firm_name", "subject_matter_number",
            "subject_matter_text",
        ])
        writer.writeheader()
        writer.writerows(out_rows)

    distinct_people = len({r["match_key"] for r in out_rows})
    print(f"Subject matter filings scanned: {len(subj_rows)}")
    print(f"  skipped (not dev-related): {skipped_not_dev}")
    print(f"  skipped (Consultant, not In-house): {skipped_not_inhouse}")
    print(f"  skipped (missing registrant name): {skipped_no_name}")
    print(f"Reference rows written: {len(out_rows)} ({distinct_people} distinct people)")
    print(f"-> {OUT_PATH}")


if __name__ == "__main__":
    main()
