"""Pull full CKAN datastore resources to data/raw/, paginating past the API's per-request limit."""
import json
import time
from pathlib import Path

import requests

BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

RESOURCES = {
    "votes_2022_2026": "55ead013-2331-4686-9895-9e8145b94189",
    "development_applications": "8907d8ed-c515-4ce9-b674-9f8c6eefcf0d",
}

PAGE_SIZE = 5000


def fetch_resource(resource_id: str) -> list[dict]:
    records = []
    offset = 0
    while True:
        r = requests.get(
            f"{BASE}/datastore_search",
            params={"resource_id": resource_id, "limit": PAGE_SIZE, "offset": offset},
            timeout=60,
        )
        r.raise_for_status()
        result = r.json()["result"]
        batch = result["records"]
        records.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        time.sleep(0.2)
    return records


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, resource_id in RESOURCES.items():
        print(f"Fetching {name} ({resource_id})...")
        records = fetch_resource(resource_id)
        out_path = RAW_DIR / f"{name}.json"
        out_path.write_text(json.dumps(records, indent=None), encoding="utf-8")
        print(f"  {len(records)} rows -> {out_path}")


if __name__ == "__main__":
    main()
