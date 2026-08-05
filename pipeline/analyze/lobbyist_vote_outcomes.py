"""
"How often do lobbyists get their way?" -- development/planning votes since
Nov 2022 (votes.csv's own earliest row -- no separate date filter needed)
connected to a registered lobbyist, using two independent linking
mechanisms:

  1. Identity match (2026-08-03, original session): a development item's
     applicant/agent/architect/owner org (from an extracted Application
     Data Sheet) merges with an existing lobbyist firm/beneficiary entity
     in the knowledge graph. Covers 61 of 241 development items.
  2. Address match (2026-08-03, this session): a lobbyist subject matter's
     free-text Particulars names the same street address as a development
     item's title. Covers 85 of 241 (46 entirely new beyond the 61).

Combined: 107 of 241 development items (44.4%) are lobbying-connected --
see pipeline/analyze/classify_lobbying_side.py -> data/processed/
lobbying_connected_items.csv, which also attempted a developer-vs-
opposition side classification. **Verified null: 0 of 107 have a
confirmed opposition-side beneficiary** -- real opposition-side registered
lobbying exists in the broader registry (37 dev-related subject matters
tied to resident/community/heritage-coalition beneficiaries) but none of
their addresses match any of the 241 Council-voted items, checked directly.
Every item this dataset covers is developer/applicant-side.

Real methodological correction from the original identity-only pass (see
docs/08 2026-08-03 entry): Community Council-level "Lost" votes do NOT mean
refusal -- Toronto forwards those items to City Council "without
recommendations" instead, and Council decides. The Clerk's own "Tracking
Status" line states the true final disposition directly, so all 123 items
across the identity+address populations were checked against it (data/raw/
dev_application_tracking_status/tracking_status.json), not reconstructed
from vote joins.

New disposition categories found in this expanded population that didn't
appear in the original 81-item sample:
  - refused: "was not adopted" (2 confirmed: 2023.CC5.24, 2025.MM32.44) --
    the first genuine refusals found across either sample.
  - received_no_action: Council received the item for information, no
    decision either way (2024.PH11.13).
  - no_recommendation: a board (here, Toronto Preservation Board) considered
    the item and issued no recommendation at all (2024.PB15.10).

Output: data/processed/lobbyist_disposition_outcomes.csv (one row per
lobbying-connected item: linked_via, link_confidence, side, disposition).
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
TRACKING_STATUS_PATH = RAW / "dev_application_tracking_status" / "tracking_status.json"
CONNECTED_PATH = PROCESSED / "lobbying_connected_items.csv"
OUT_PATH = PROCESSED / "lobbyist_disposition_outcomes.csv"


def load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_disposition(text):
    t = text.lower()
    if "was not adopted" in t or re.search(r"\brefus", t):
        return "refused"
    if "received" in t and "for information" in t:
        return "received_no_action"
    if "without recs" in t or "no recommendation" in t:
        return "no_recommendation"
    if "postponed" in t or "deferred" in t or "referred" in t:
        return "deferred_or_referred"
    if re.search(r"city council adopted this item.*?(with|without) amendments", t):
        m = re.search(r"(with|without) amendments", t)
        return "adopted_with_amendment" if m.group(1) == "with" else "adopted_without_amendment"
    if "adopted" in t:
        return "adopted_with_amendment" if "with amendment" in t else "adopted_without_amendment"
    return "unknown"


def main():
    connected = load_csv(CONNECTED_PATH)
    tracking_status = json.loads(TRACKING_STATUS_PATH.read_text(encoding="utf-8"))

    rows_out = []
    for r in connected:
        text = tracking_status.get(r["item_id"], "")
        rows_out.append({
            "item_id": r["item_id"],
            "agenda_item_title": r["agenda_item_title"],
            "linked_via": r["linked_via"],
            "link_confidence": r["link_confidence"],
            "side": r["side"],
            "disposition": parse_disposition(text),
            "tracking_status_text": text,
        })

    PROCESSED.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)

    def report(label, rows):
        n = len(rows)
        by_disp = {}
        for r in rows:
            by_disp[r["disposition"]] = by_disp.get(r["disposition"], 0) + 1
        adopted = by_disp.get("adopted_with_amendment", 0) + by_disp.get("adopted_without_amendment", 0)
        print(f"{label}: n={n}, adopted={adopted} ({100*adopted/n:.1f}%)" if n else f"{label}: n=0")
        for k, v in sorted(by_disp.items(), key=lambda kv: -kv[1]):
            print(f"    {k}: {v}")

    print(f"Total lobbying-connected development items: {len(rows_out)} of 241\n")
    report("ALL lobbying-connected items", rows_out)
    print()
    report("  identity-only", [r for r in rows_out if r["linked_via"] == "identity"])
    report("  address-only", [r for r in rows_out if r["linked_via"] == "address"])
    report("  both mechanisms", [r for r in rows_out if r["linked_via"] == "identity+address"])
    print()
    report("  street_type_matched confidence", [r for r in rows_out if r["link_confidence"] == "street_type_matched"])
    report("  street_type_mismatch_or_missing confidence", [r for r in rows_out if r["link_confidence"] == "street_type_mismatch_or_missing"])
    print(f"\n-> {OUT_PATH}")


if __name__ == "__main__":
    main()
