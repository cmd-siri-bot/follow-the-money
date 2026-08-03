"""Normalize the five EFD contribution exports (2022 general + 4 by-elections) into a
single interim table. Each source file covers a distinct election event; by-election
winners' donors only appear in their own by-election's file, not the 2022 general one.
"""
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "efd_contributions"
INTERIM_DIR = Path(__file__).resolve().parent.parent / "data" / "interim"

# (filename, election label, election year)
SOURCES = [
    ("2022_general_election.xls", "2022 Municipal Election", 2022),
    ("2023_mayor_byelection.xls", "2023 Mayoral By-Election", 2023),
    ("2023_ward20_byelection.xls", "2023 Ward 20 By-Election", 2023),
    ("2024_ward15_byelection.xls", "2024 Ward 15 By-Election", 2024),
    ("2025_ward25_byelection.xls", "2025 Ward 25 By-Election", 2025),
]

COLUMN_MAP = {
    "Contributor ": "contributor",
    "Postal Code ": "postal_code",
    "Amount": "amount",
    "Amount Returned": "amount_returned",
    "Contribution Type": "contribution_type",
    "Description of\n Goods/Services": "description",
    "Contributor Type": "contributor_type",
    "Date Contribution \nReceived": "date_received",
    "Candidate /\nRegistrant": "candidate",
    "Registered for": "office",
    "Ward": "ward",
    "Registrant Type": "registrant_type",
}


def load_one(filename: str, election: str, election_year: int) -> pd.DataFrame:
    df = pd.read_excel(RAW_DIR / filename, header=7)
    df = df.rename(columns=COLUMN_MAP)
    df["source_file"] = filename
    df["election"] = election
    df["election_year"] = election_year
    df["date_received"] = pd.to_datetime(df["date_received"], format="%b %d, %Y", errors="coerce")
    df["has_encoding_issue"] = (
        df["contributor"].astype(str).str.contains("�")
        | df["candidate"].astype(str).str.contains("�")
    )
    return df


def main():
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    frames = [load_one(*src) for src in SOURCES]
    combined = pd.concat(frames, ignore_index=True)

    out_path = INTERIM_DIR / "contributions.csv"
    combined.to_csv(out_path, index=False)

    print(f"{len(combined)} total rows -> {out_path}")
    print("\nBy election:")
    print(combined.groupby("election").size())
    print("\nBy office:")
    print(combined.groupby("office").size())
    print("\nRows with encoding issues:", combined["has_encoding_issue"].sum())
    print("Rows with unparsed dates:", combined["date_received"].isna().sum())


if __name__ == "__main__":
    main()
