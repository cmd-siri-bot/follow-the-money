"""Pull full CKAN datastore resources to data/raw/, paginating past the API's per-request limit."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from common.ckan_client import fetch_resource  # noqa: E402

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

RESOURCES = {
    "votes_2022_2026": "55ead013-2331-4686-9895-9e8145b94189",
    "development_applications": "8907d8ed-c515-4ce9-b674-9f8c6eefcf0d",
}


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
