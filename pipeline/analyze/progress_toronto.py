"""
Progress Toronto donor rundown.

Not a new data pull -- contributions.csv already contains third-party
advertiser (TPA) contributions from the same 5 raw EFD exports used for
candidate contributions (`office == "Third Party Advertiser"`, 146 rows
total across all TPAs; 132 of those are Progress Toronto specifically).
classify_donors.py excludes all TPA rows by design (docs/01/08: "Third
party advertisers deferred to v2 for candidate-affiliation scoring") --
that decision is about not mixing TPA money into the candidate donor
population, not about the TPA data not existing. This is a standalone
analysis reusing normalize_names.py against the existing dev_sector
reference list, same as Signal 3, but is NOT merged into donors.csv or
the knowledge graph built for the lobbyist deep-dive.

Output: data/processed/progress_toronto_donors.csv (one row per
contribution, plus a name-match flag against dev_sector_reference.csv)
"""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "transform"))
from normalize_names import normalize_name  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"

CONTRIB_PATH = INTERIM / "contributions.csv"
DEV_REF_PATH = INTERIM / "dev_sector_reference.csv"
OUT_PATH = PROCESSED / "progress_toronto_donors.csv"

TARGET = "Progress Toronto"


def load(path):
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    contributions = load(CONTRIB_PATH)
    dev_ref = load(DEV_REF_PATH)
    dev_ref_keys = {r["match_key"] for r in dev_ref}

    rows = [r for r in contributions if r["candidate"] == TARGET]

    out_rows = []
    for r in rows:
        amount = float(r["amount"] or 0)
        returned = float(r["amount_returned"] or 0)
        amount_net = max(amount - returned, 0)
        norm = normalize_name(r["contributor"])
        dev_match = norm["match_key"] in dev_ref_keys
        out_rows.append({
            "contributor": r["contributor"],
            "contributor_type": r["contributor_type"],
            "postal_code": r["postal_code"],
            "amount": amount,
            "amount_returned": returned,
            "amount_net": amount_net,
            "date_received": r["date_received"],
            "contribution_type": r["contribution_type"],
            "election": r["election"],
            "dev_sector_reference_name_match": dev_match,
        })

    PROCESSED.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    total_net = sum(r["amount_net"] for r in out_rows)
    distinct_donors = len({(normalize_name(r["contributor"])["match_key"], r["postal_code"]) for r in rows})
    by_election = {}
    for r in out_rows:
        by_election.setdefault(r["election"], {"n": 0, "net": 0.0})
        by_election[r["election"]]["n"] += 1
        by_election[r["election"]]["net"] += r["amount_net"]

    by_type = {}
    for r in out_rows:
        by_type[r["contributor_type"]] = by_type.get(r["contributor_type"], 0) + 1

    dev_matches = [r for r in out_rows if r["dev_sector_reference_name_match"]]

    # repeat donors across multiple elections
    donor_elections = {}
    for r in rows:
        key = (normalize_name(r["contributor"])["match_key"], r["postal_code"])
        donor_elections.setdefault(key, set()).add(r["election"])
    repeat_donors = {k: v for k, v in donor_elections.items() if len(v) > 1}

    print(f"Progress Toronto: {len(out_rows)} contributions, {distinct_donors} distinct donors, ${total_net:,.2f} net")
    print()
    print("By election:")
    for election, d in sorted(by_election.items()):
        print(f"  {election}: {d['n']} contributions, ${d['net']:,.2f}")
    print()
    print("By contributor_type:")
    for k, v in sorted(by_type.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")
    print()
    print(f"Donors who gave in more than one election: {len(repeat_donors)}")
    print()
    print(f"Name matches against dev_sector_reference.csv (lobbyist registry, name-only -- same caveat as Signal 3, not proof of identity): {len(dev_matches)}")
    for r in dev_matches:
        print(f"  {r['contributor']}  ${r['amount_net']}  {r['election']}")
    print()
    print(f"Top 15 by amount_net:")
    for r in sorted(out_rows, key=lambda r: -r["amount_net"])[:15]:
        print(f"  {r['contributor']:<35} ${r['amount_net']:>8.2f}  {r['election']}  {r['contributor_type']}")
    print()
    print(f"-> {OUT_PATH}")


if __name__ == "__main__":
    main()
