"""Clean the Development Applications dataset (data/raw/development_applications.json)
into data/interim/development_applications.csv: snake_case columns, typed dates/ward numbers.
"""
import json
from pathlib import Path

import pandas as pd

RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "development_applications.json"
INTERIM_DIR = Path(__file__).resolve().parent.parent / "data" / "interim"

COLUMN_MAP = {
    "APPLICATION_TYPE": "application_type",
    "APPLICATION#": "application_number",
    "STREET_NUM": "street_num",
    "STREET_NAME": "street_name",
    "STREET_TYPE": "street_type",
    "STREET_DIRECTION": "street_direction",
    "POSTAL": "postal_code",
    "DATE_SUBMITTED": "date_submitted",
    "STATUS": "status",
    "X": "x",
    "Y": "y",
    "DESCRIPTION": "description",
    "REFERENCE_FILE#": "reference_file_number",
    "FOLDERRSN": "folder_rsn",
    "WARD_NUMBER": "ward_number",
    "WARD_NAME": "ward_name",
    "COMMUNITY_MEETING_DATE": "community_meeting_date",
    "COMMUNITY_MEETING_TIME": "community_meeting_time",
    "COMMUNITY_MEETING_LOCATION": "community_meeting_location",
    "APPLICATION_URL": "application_url",
    "CONTACT_NAME": "contact_name",
    "CONTACT_PHONE": "contact_phone",
    "CONTACT_EMAIL": "contact_email",
    "PARENT_FOLDER_NUMBER": "parent_folder_number",
}


def main():
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    records = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    df = pd.DataFrame(records).drop(columns=["_id"])
    df = df.rename(columns=COLUMN_MAP)

    df["date_submitted"] = pd.to_datetime(df["date_submitted"], errors="coerce")
    df["community_meeting_date"] = pd.to_datetime(df["community_meeting_date"], errors="coerce")
    df["ward_number"] = pd.to_numeric(df["ward_number"], errors="coerce").astype("Int64")

    out_path = INTERIM_DIR / "development_applications.csv"
    df.to_csv(out_path, index=False)

    print(f"{len(df)} rows -> {out_path}")
    print("Unparsed date_submitted:", df["date_submitted"].isna().sum())
    print("Unparsed ward_number:", df["ward_number"].isna().sum())
    print("Date range:", df["date_submitted"].min(), "to", df["date_submitted"].max())


if __name__ == "__main__":
    main()
