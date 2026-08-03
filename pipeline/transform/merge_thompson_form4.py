"""
Append Michael Thompson's Form 4 contributions (transcribed and checksummed
by thompson_form4_transcription.py) into the main contributions.csv, using
the exact same column schema as the EFD bulk export so downstream code
(normalize/classify) doesn't need a second code path.

Idempotent: does nothing if Thompson rows are already present, so it's safe
to include in a full pipeline re-run.

Source: data/raw/efd_contributions/2022_thompson_ward21_form4.pdf (user-
provided, filed with the City Clerk 2023-03-29, campaign period 2022-05-30
to 2023-01-03, election held 2022-10-24). See docs/08-decision-log.md
2026-08-02 "Michael Thompson data gap resolved" for full provenance.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THOMPSON_CSV = ROOT / "data" / "interim" / "thompson_form4_contributions.csv"
CONTRIBUTIONS_CSV = ROOT / "data" / "interim" / "contributions.csv"

CANDIDATE = "Thompson, Michael"
SOURCE_FILE = "2022_thompson_ward21_form4.pdf"
ELECTION = "2022 Municipal Election"
ELECTION_YEAR = 2022


def main():
    with CONTRIBUTIONS_CSV.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        existing_rows = list(reader)

    if any(r["candidate"] == CANDIDATE for r in existing_rows):
        print("Thompson rows already present in contributions.csv -- skipping (idempotent).")
        return

    with THOMPSON_CSV.open("r", newline="", encoding="utf-8") as f:
        thompson_rows = list(csv.DictReader(f))

    new_rows = []
    for r in thompson_rows:
        contributor = f"{r['last_name'].strip()}, {r['first_name'].strip()}"
        new_rows.append({
            "contributor": contributor,
            "postal_code": r["postal_code"],
            "amount": r["amount"],
            "amount_returned": "",
            "contribution_type": "Monetary",
            "description": "",
            "contributor_type": "Individual",
            "date_received": r["date_received"],
            "candidate": CANDIDATE,
            "office": "Councillor",
            "ward": "21",
            "registrant_type": "",
            "source_file": SOURCE_FILE,
            "election": ELECTION,
            "election_year": str(ELECTION_YEAR),
            "has_encoding_issue": "False",
        })

    all_rows = existing_rows + new_rows
    with CONTRIBUTIONS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Appended {len(new_rows)} Thompson rows. contributions.csv now has {len(all_rows)} total rows "
          f"(was {len(existing_rows)}).")


if __name__ == "__main__":
    main()
