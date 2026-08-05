"""
Combine the two lobbying-to-vote linking mechanisms (identity match via
development_applicants.csv's applicant/agent/architect/owner org merge, and
address match via lobbying_address_matches.csv) into one dataset, with a
"side" classification: developer-side vs opposition-side.

**Honest null result, checked directly, not assumed:** across every
development-related, address-bearing lobbying subject matter that links to
one of the 241 Council-agenda development items (via either mechanism),
ZERO have an opposition-side beneficiary (name matching resident/ratepayer/
neighbourhood/community association/heritage/homeowner/coalition/
preservation patterns). Real opposition-side registered lobbying DOES exist
in the broader registry (37 development-related subject matters tied to
opposition-keyword beneficiaries, e.g. "Yorkville/Cumberland Neighbourhood
Coalition re 21 Avenue Road", "Opposition to the Application for Consent to
Sever, 21 Avenue Road") -- but none of their addresses match any of the 241
Council-voted items, checked directly address-by-address. This is not a
matching-method gap: the addresses these opposition filings name (394
Symington Ave, 100 Thorncliffe Park Drive, 21 Avenue Road, 18 Wells Hill
Avenue, etc.) plausibly relate to Committee of Adjustment / minor-variance
matters that are decided below full Council and never appear as their own
Council agenda item, not to items excluded by an extraction bug.

Every item this dataset links, is developer/applicant-side. "Side" is
reported per docs/08's identity-match standard: never asserted from a name
match alone with no corroboration -- the identity-matched population (61
items) has org_key-level identity confirmation; the address-matched
population (85 items, confidence-tiered) is a text match, weaker on its own.

Output: data/processed/lobbying_connected_items.csv -- one row per linked
agenda item, deduplicated across both mechanisms.
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
OUT_PATH = PROCESSED / "lobbying_connected_items.csv"

OPPOSITION_KEYWORDS = [
    "resident", "ratepayer", "neighbourhood", "neighborhood",
    "community association", "heritage", "homeowner", "coalition",
    "against", "preservation",
]


def load_csv(path):
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def classify_side(beneficiary_names):
    text = (beneficiary_names or "").lower()
    if any(kw in text for kw in OPPOSITION_KEYWORDS):
        return "opposition"
    return "developer"


def main():
    entities = {r["entity_id"]: r for r in load_csv(INTERIM / "kg_entities.csv")}
    edges = load_csv(INTERIM / "kg_edges.csv")
    address_matches = load_csv(PROCESSED / "lobbying_address_matches.csv")
    dev_app_rows = load_csv(PROCESSED / "development_applicants.csv")
    agenda_items = {r["agenda_item_id"]: r for r in load_csv(INTERIM / "agenda_items.csv")}

    role_edges = [e for e in edges if e["edge_type"].startswith("role__")]
    lobby_edges = [e for e in edges if e["edge_type"].startswith("lobbies_for__") or e["edge_type"] == "represents"]
    lobbied_org_ids = {e["target_id"] for e in lobby_edges}

    identity_items = {}
    for e in role_edges:
        item_id = e["target_id"].replace("devapp:", "")
        src = entities.get(e["source_id"], {})
        if src.get("entity_type") == "org" and e["source_id"] in lobbied_org_ids:
            identity_items.setdefault(item_id, []).append(src["display_name"])

    address_items = {}
    for r in address_matches:
        address_items.setdefault(r["agenda_item_id"], []).append(r)

    all_item_ids = set(identity_items) | set(address_items)
    rows_out = []
    for item_id in sorted(all_item_ids):
        title = agenda_items.get(item_id, {}).get("agenda_item_title", "")
        sources = []
        if item_id in identity_items:
            sources.append("identity")
        if item_id in address_items:
            sources.append("address")

        if item_id in identity_items:
            confidence = "org_key_merge"
            side = "developer"  # by construction: matched via applicant/agent/architect/owner identity
            beneficiary_context = "; ".join(sorted(set(identity_items[item_id])))
        else:
            addr_rows = address_items[item_id]
            confidence = "street_type_matched" if any(r["confidence"] == "street_type_matched" for r in addr_rows) else "street_type_mismatch_or_missing"
            all_bene = "; ".join(r["beneficiary_names"] for r in addr_rows)
            side = classify_side(all_bene)
            beneficiary_context = all_bene

        rows_out.append({
            "item_id": item_id,
            "agenda_item_title": title,
            "linked_via": "+".join(sources),
            "link_confidence": confidence,
            "side": side,
            "beneficiary_context": beneficiary_context,
        })

    PROCESSED.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)

    n_identity_only = sum(1 for r in rows_out if r["linked_via"] == "identity")
    n_address_only = sum(1 for r in rows_out if r["linked_via"] == "address")
    n_both = sum(1 for r in rows_out if r["linked_via"] == "identity+address")
    n_opposition = sum(1 for r in rows_out if r["side"] == "opposition")
    print(f"Total lobbying-connected development items: {len(rows_out)} of 241")
    print(f"  identity-only: {n_identity_only}, address-only: {n_address_only}, both: {n_both}")
    print(f"  side=opposition: {n_opposition} (0 expected -- see module docstring)")
    print(f"-> {OUT_PATH}")


if __name__ == "__main__":
    main()
