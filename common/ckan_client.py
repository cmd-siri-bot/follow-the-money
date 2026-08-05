"""Generic City of Toronto CKAN datastore client, shared by Follow the Money
and TorontoSpends. Paginates past the API's per-request row limit.
"""
import json
import time
from pathlib import Path

import requests

BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action"
PAGE_SIZE = 5000


def fetch_resource(resource_id: str, page_size: int = PAGE_SIZE) -> list[dict]:
    records = []
    offset = 0
    while True:
        r = requests.get(
            f"{BASE}/datastore_search",
            params={"resource_id": resource_id, "limit": page_size, "offset": offset},
            timeout=60,
        )
        r.raise_for_status()
        result = r.json()["result"]
        batch = result["records"]
        records.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
        time.sleep(0.2)
    return records


def fetch_and_save(resource_id: str, out_path: Path) -> list[dict]:
    """Fetch a resource and archive the raw response to disk, per this
    project's standing 'archive the raw' discipline -- every fact row
    needs to trace back to what was actually retrieved, not just the
    transformed result."""
    records = fetch_resource(resource_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, indent=None), encoding="utf-8")
    return records


def resource_download_url(resource_id: str) -> str:
    """For non-datastore resources published as a single downloadable
    file (XLSX/ZIP/etc, no datastore_search table) -- looks up the real
    file URL via resource_show rather than guessing the URL pattern."""
    r = requests.get(f"{BASE}/resource_show", params={"id": resource_id}, timeout=30)
    r.raise_for_status()
    return r.json()["result"]["url"]


def fetch_file(resource_id: str, out_path: Path, force: bool = False) -> Path:
    """Download a non-datastore resource's file to out_path, caching it
    (skip re-download if out_path already exists) unless force=True."""
    if out_path.exists() and not force:
        return out_path
    url = resource_download_url(resource_id)
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(r.content)
    return out_path
