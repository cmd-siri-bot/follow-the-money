"""
Per-member cross-cut of the knowledge graph (build_knowledge_graph.py)
against Phase 3's existing dev_affiliation_share, plus the graph's most
direct "connections to power" finding: registrants (lobbyists) who both
contacted a member's office AND appear, via a possible_same_person edge,
as a donor to that same member.

This does not re-run or alter Phase 3 -- candidate_donor_mix.csv is read
as-is, base threshold (0.5) rows only, for context alongside the new
lobbying-contact numbers. No site/publication output; this is analysis
only, per the deep-dive's deliverable decision (standalone side
investigation, scoped 2026-08-03).

Output: data/processed/kg_member_summary.csv
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"

ENTITIES_PATH = INTERIM / "kg_entities.csv"
EDGES_PATH = INTERIM / "kg_edges.csv"
MEMBERS_PATH = INTERIM / "member_terms.csv"
MIX_PATH = PROCESSED / "candidate_donor_mix.csv"

OUT_PATH = PROCESSED / "kg_member_summary.csv"


def load_csv(path):
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    edges = load_csv(EDGES_PATH)
    members = load_csv(MEMBERS_PATH)
    mix_rows = load_csv(MIX_PATH)

    mix_base = {r["member_id"]: r for r in mix_rows if r["threshold_setting"] == "0.5"}

    lobbied_office_edges = [e for e in edges if e["edge_type"] == "lobbied_office"]
    donated_edges = [e for e in edges if e["edge_type"] == "donated"]
    same_person_edges = [e for e in edges if e["edge_type"] == "possible_same_person"]

    # donor_id -> set of member entity_ids they donated to
    donor_to_members = {}
    for e in donated_edges:
        donor_to_members.setdefault(e["source_id"], set()).add(e["target_id"])

    # registrant_id -> [(donor_id, confidence), ...]
    registrant_to_donors = {}
    for e in same_person_edges:
        registrant_to_donors.setdefault(e["source_id"], []).append((e["target_id"], e["confidence"]))

    # member entity_id -> set of registrant_ids who lobbied that office
    member_to_lobbyists = {}
    member_lobby_contact_count = {}
    for e in lobbied_office_edges:
        member_to_lobbyists.setdefault(e["target_id"], set()).add(e["source_id"])
        member_lobby_contact_count[e["target_id"]] = member_lobby_contact_count.get(e["target_id"], 0) + 1

    rows_out = []
    for m in members:
        member_entity_id = f"member:{m['member_id']}"
        mix = mix_base.get(m["member_name"], {})
        lobbyists = member_to_lobbyists.get(member_entity_id, set())

        # lobbyists who contacted this member's office AND are a possible
        # donor to this SAME member (the direct "money + access" overlap),
        # split by identity-match confidence -- corroborated (shared
        # postal code, same as Signal 1's corroboration logic) is the
        # defensible number; name_only is a lead, not a finding.
        overlap_corroborated = 0
        overlap_uncorroborated = 0
        for reg_id in lobbyists:
            for donor_id, confidence in registrant_to_donors.get(reg_id, []):
                if member_entity_id in donor_to_members.get(donor_id, set()):
                    if confidence == "name_and_postal_corroborated":
                        overlap_corroborated += 1
                    else:
                        overlap_uncorroborated += 1

        rows_out.append({
            "member_id": m["member_id"],
            "member_name": m["member_name"],
            "ward_number": m["ward_number"],
            "office": m["office"],
            "is_current": "" == m["end_date"],
            "dev_affiliation_share": mix.get("dev_affiliation_share", ""),
            "ward_development_intensity": mix.get("ward_development_intensity", ""),
            "n_donors_phase3": mix.get("n_donors", ""),
            "distinct_lobbyists_contacted_office": len(lobbyists),
            "total_lobbying_contacts_to_office": member_lobby_contact_count.get(member_entity_id, 0),
            "lobbyist_donor_overlap_corroborated": overlap_corroborated,
            "lobbyist_donor_overlap_name_only": overlap_uncorroborated,
        })

    PROCESSED.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows_out[0].keys())
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_out)

    current_rows = [r for r in rows_out if r["is_current"]]
    print(f"Members summarized: {len(rows_out)} ({len(current_rows)} current)")
    print(f"-> {OUT_PATH}")
    print()
    print("Current members, sorted by distinct lobbyists who contacted their office:")
    for r in sorted(current_rows, key=lambda r: -r["distinct_lobbyists_contacted_office"])[:10]:
        print(f"  {r['member_name']:<25} lobbyists={r['distinct_lobbyists_contacted_office']:>4}  "
              f"contacts={r['total_lobbying_contacts_to_office']:>5}  "
              f"dev_share={r['dev_affiliation_share']}  "
              f"corroborated overlap={r['lobbyist_donor_overlap_corroborated']}  "
              f"name-only overlap={r['lobbyist_donor_overlap_name_only']}")
    print()
    total_corroborated = sum(r["lobbyist_donor_overlap_corroborated"] for r in rows_out)
    total_name_only = sum(r["lobbyist_donor_overlap_name_only"] for r in rows_out)
    corroborated_members = [r for r in current_rows if r["lobbyist_donor_overlap_corroborated"] > 0]
    print(f"CORROBORATED lobbyist<->same-member-donor overlaps (shared postal code, not just name): {total_corroborated}")
    print(f"  current members with at least one: {len(corroborated_members)} of {len(current_rows)}")
    for r in corroborated_members:
        print(f"    {r['member_name']}: {r['lobbyist_donor_overlap_corroborated']}")
    print(f"Name-only (uncorroborated) overlaps -- leads, not findings, per docs/02's identity-match standard: {total_name_only}")


if __name__ == "__main__":
    main()
