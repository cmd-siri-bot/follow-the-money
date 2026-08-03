"""Clean the councillor voting record (data/raw/votes_2022_2026.json) into
data/interim/votes.csv. Renames columns to snake_case and parses Date/Time,
which is inconsistently formatted: it's 24-hour time with a spurious literal
"AM"/"PM" suffix that doesn't follow real 12-hour convention (e.g. "21:27 PM"),
and some rows have no time component at all.
"""
import json
import re
from pathlib import Path

import pandas as pd

RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "votes_2022_2026.json"
INTERIM_DIR = Path(__file__).resolve().parent.parent / "data" / "interim"

COLUMN_MAP = {
    "Term": "term",
    "First Name": "first_name",
    "Last Name": "last_name",
    "Committee": "committee",
    "Date/Time": "date_time_raw",
    "Agenda Item #": "agenda_item_number",
    "Agenda Item Title": "agenda_item_title",
    "Motion Type": "motion_type",
    "Vote": "vote",
    "Result": "result",
    "Vote Description": "vote_description",
}


def parse_date_time(raw: str):
    if not raw or pd.isna(raw):
        return pd.NaT
    stripped = re.sub(r"\s*(AM|PM)\s*$", "", raw.strip())
    if re.match(r"^\d{4}-\d{2}-\d{2}$", stripped):
        return pd.to_datetime(stripped, format="%Y-%m-%d", errors="coerce")
    return pd.to_datetime(stripped, format="%Y-%m-%d %H:%M", errors="coerce")


def main():
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    records = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    df = pd.DataFrame(records).drop(columns=["_id"])
    df = df.rename(columns=COLUMN_MAP)
    df["date_time"] = df["date_time_raw"].apply(parse_date_time)

    out_path = INTERIM_DIR / "votes.csv"
    df.to_csv(out_path, index=False)

    print(f"{len(df)} rows -> {out_path}")
    print("Unparsed date_time:", df["date_time"].isna().sum())
    print("Vote value counts:")
    print(df["vote"].value_counts())
    print("Unique members:", df[["first_name", "last_name"]].drop_duplicates().shape[0])
    print("Unique agenda items:", df["agenda_item_number"].nunique())


if __name__ == "__main__":
    main()
