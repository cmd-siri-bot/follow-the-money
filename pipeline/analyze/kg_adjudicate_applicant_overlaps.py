"""
General (not hand-enumerated) adjudication worksheet over every
postal-code-corroborated possible_same_person edge in the knowledge
graph -- both source populations:

  1. lobbyist_registrant <-> donor (the original link_registrants_to_donors
     pass from the 2026-08-03 "Lobbyist/donor deep-dive" session)
  2. dev_role_person <-> donor/lobbyist_registrant (the 2026-08-03
     "graph-enhancement name-matching" addition -- applicant/agent/
     architect/owner names extracted from development_applicants.csv)

This supersedes kg_adjudicate_overlaps.py's fixed 8-pair list, which was
built BEFORE a real bug was caught and fixed: registrant postal codes in
lobbyist_subject_matters.csv are ~76% formatted with an internal space
("M5T 2C8") while donors.csv's postal_code column never has one
("M5T2C8") -- comparing them raw meant only the ~24% space-free
registrants could ever be flagged as corroborated. normalize_postal()
(pipeline/transform/normalize_names.py) fixes this at the source. Net
effect: registrant<->donor corroborated matches went from 39 to 148 --
the original 8 hand-adjudicated rows are still valid corroborated
matches (all had space-free postal codes, which is exactly why they
weren't affected by the bug), but they were never a representative or
complete sample.

At 149 rows, hand-written prose notes per pair (kg_adjudicate_overlaps.py's
approach) isn't practical -- the structured columns here ARE the LLM
first-cut evidence. reviewer_verdict/reviewer_note stay blank for the
user's own read, same standard as audit/donor_review.csv and the
original kg_lobbyist_donor_overlap_review.csv.

Output: audit/kg_corroborated_overlaps_review.csv
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
OUT_PATH = ROOT / "audit" / "kg_corroborated_overlaps_review.csv"


def load(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    entities = {r["entity_id"]: r for r in load(INTERIM / "kg_entities.csv")}
    edges = load(INTERIM / "kg_edges.csv")
    donors = load(INTERIM / "donors.csv")
    members = {f"member:{r['member_id']}": r for r in load(INTERIM / "member_terms.csv")}

    donated_edges = [e for e in edges if e["edge_type"] == "donated"]
    lobbied_office_edges = [e for e in edges if e["edge_type"] == "lobbied_office"]
    role_edges = [e for e in edges if e["edge_type"].startswith("role__")]

    donor_donations = {}
    for e in donated_edges:
        donor_donations.setdefault(e["source_id"], []).append(e)
    registrant_offices = {}
    for e in lobbied_office_edges:
        registrant_offices.setdefault(e["source_id"], []).append(e)
    person_roles = {}
    for e in role_edges:
        person_roles.setdefault(e["source_id"], []).append(e)

    def donor_summary(donor_id):
        rows = donor_donations.get(donor_id, [])
        if not rows:
            return 0.0, ""
        total = sum(float(r["amount"]) for r in rows if r["amount"])
        detail = "; ".join(f"{r['date']} ${r['amount']}->{members.get(r['target_id'], {}).get('member_name', '?')}" for r in rows)
        return round(total, 2), detail

    def registrant_office_summary(registrant_id):
        rows = registrant_offices.get(registrant_id, [])
        if not rows:
            return 0, ""
        dates = sorted(r["date"] for r in rows if r["date"])
        offices = sorted({members.get(r["target_id"], {}).get("member_name", "?") for r in rows})
        date_range = f"{dates[0]} to {dates[-1]}" if dates else ""
        return len(rows), f"offices={'; '.join(offices)}; contacts={len(rows)}; dates={date_range}"

    def role_summary(person_id):
        rows = person_roles.get(person_id, [])
        return "; ".join(f"{r['edge_type'].replace('role__', '')} on {r['basis'].split(':')[0]}" for r in rows)

    rows_out = []
    for e in edges:
        if e["edge_type"] != "possible_same_person" or e["confidence"] != "name_and_postal_corroborated":
            continue
        src = entities.get(e["source_id"], {})
        tgt = entities.get(e["target_id"], {})
        source_kind = src.get("subtype", "")
        target_kind = tgt.get("subtype", "")

        row = {
            "shared_postal_code": src.get("postal_code", ""),
            "source_kind": source_kind,
            "source_name": src.get("display_name", ""),
            "source_notes": src.get("notes", ""),
            "target_kind": target_kind,
            "target_name": tgt.get("display_name", ""),
        }

        if source_kind == "dev_role_person":
            row["source_context"] = role_summary(e["source_id"])
        else:
            n_contacts, office_detail = registrant_office_summary(e["source_id"])
            row["source_context"] = office_detail

        if target_kind == "donor":
            total, detail = donor_summary(e["target_id"])
            row["target_context"] = f"total_net=${total}; {detail}"
        elif target_kind == "lobbyist_registrant":
            n_contacts, office_detail = registrant_office_summary(e["target_id"])
            row["target_context"] = office_detail
        else:
            row["target_context"] = ""

        row["reviewer_verdict"] = ""
        row["reviewer_note"] = ""
        rows_out.append(row)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)

    n_reg_donor = sum(1 for r in rows_out if r["source_kind"] == "lobbyist_registrant")
    n_applicant = sum(1 for r in rows_out if r["source_kind"] == "dev_role_person")
    print(f"Wrote {len(rows_out)} postal-corroborated rows -> {OUT_PATH}")
    print(f"  registrant<->donor: {n_reg_donor}")
    print(f"  dev_role_person<->donor/registrant: {n_applicant}")


if __name__ == "__main__":
    main()
