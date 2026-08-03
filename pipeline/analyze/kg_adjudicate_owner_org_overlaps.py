"""
Manual adjudication pass on the 14 "owner-only" organization cross-
validation hits from the 2026-08-03 graph-enhancement session (see
docs/08-decision-log.md): a development-application Owner name that
already existed in the graph as a lobbyist firm/beneficiary org, but did
NOT also appear as that application's applicant/agent/architect --
i.e. the property-owning entity itself, not just its hired consultants,
has an existing lobbying relationship.

Same LLM-first-cut-then-human-review pattern as
kg_adjudicate_overlaps.py, with one addition: lobbied_office contacts are
filtered to the SAME subject_matter_number as the represents/lobbies_for
edge to this specific org, not a registrant's total contact count across
every client they've ever represented -- several of these registrants
(Tristan Downe-Dewdney, Amir Remtulla, Aidan Grove-White) have hundreds
of contacts spanning many unrelated files, and reporting that raw total
next to a single property would be misleading.

reviewer_verdict/reviewer_note blank for the user's own read, same
standard as every other adjudication file in this project.

Output: audit/kg_owner_org_overlap_review.csv
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
OUT_PATH = ROOT / "audit" / "kg_owner_org_overlap_review.csv"

# match_key (as computed by build_knowledge_graph.py's org_key()) for the
# 14 owner-only orgs identified in the 2026-08-03 session.
ORG_MATCH_KEYS = [
    "cp reit ontario properties", "pinemount developments", "queen kingston holdings",
    "microbjo properties", "1001184476 ontario", "parc downsview park",
    "2872136 ontario", "manulife ontario property portfolio", "2724471 ontario",
    "slh lakeshore", "12723638 canada", "brad jay investments",
    "crestview investment", "toronto community housing",
]

SM_RE = re.compile(r"(SM\d+)")

NOTES = {
    "cp reit ontario properties": (
        "985 Woodbine Ave / 2078-2106 Danforth Ave. Represented across 5 subject "
        "matters by 3 different consultants plus a lawyer; filtered to the SAME "
        "subject matter, only 2 of 5 show any lobbied-office contact at all (Gary "
        "Crawford x1, Frances Nunziata x1) -- thin. The lead registrant, Amir "
        "Remtulla, is otherwise extremely active (151 total contacts, 22 offices) "
        "across many unrelated clients -- that volume has nothing to do with this "
        "property and would be misleading if quoted unfiltered."
    ),
    "pinemount developments": (
        "3406-3434 Weston Road. 4 registrants across 4 subject matters. Joe Mihevc "
        "(the same Joe Mihevc named in the prior session's registrant-donor "
        "adjudication -- donated to both Matlow's and Perruzza's 2023 mayoral bids) "
        "is the most active: 11 lobbied-office contacts tied to this exact subject "
        "matter (SM36654), across 11 different councillors in a tight "
        "May 27-June 25, 2025 window, including Perruzza and Chow. The single most "
        "concentrated same-subject-matter lobbying push found among these 14."
    ),
    "queen kingston holdings": (
        "1698 Queen St E. One registrant (Tony Volpentesta), zero lobbied-office "
        "contacts tied to this subject matter -- no access pattern visible in this "
        "data."
    ),
    "microbjo properties": (
        "25 St. Mary Street (Rental Housing Demolition application). 4 registrants "
        "across 5 subject matters. Tristan Downe-Dewdney (see also 2724471 Ontario "
        "and Crestview Investment below -- same person, 1,174 total contacts across "
        "24 offices generally) shows real same-subject-matter activity here across "
        "4 of his 5 SMs: Gord Perks contacted repeatedly (11 contacts total across "
        "3 SMs, April 2024-November 2025) plus single contacts to Burnside, Moise, "
        "Matlow, Chow, Carroll, Myers, Colle, Morley, Bravo. Perks is the one office "
        "touched across nearly every subject matter tied to this file."
    ),
    "1001184476 ontario": (
        "3307/3313 Ellesmere Road. One registrant (Michael Testaguzza), 3 contacts "
        "to Neethan Shan tied to this subject matter, Dec 2025-Apr 2026 -- "
        "straightforward single-councillor pattern."
    ),
    "parc downsview park": (
        "1377 Sheppard Ave W. One registrant (David Bronskill, lawyer), zero "
        "lobbied-office contacts tied to this subject matter. Note: Parc Downsview "
        "Park Inc. is itself a federal Crown corporation, not a private developer -- "
        "changes the character of any finding here even where contacts exist."
    ),
    "2872136 ontario": (
        "2823-2829 Eglinton Ave E. 2 registrants; Kevin Wassermuhl is the active "
        "one -- 20 lobbied-office contacts tied to this exact subject matter, "
        "concentrated on Parthi Kandavel (9 contacts, Apr-May 2025) and Michael "
        "Thompson (5 contacts, May-June 2025), the ward's own councillors, plus "
        "smaller counts to Ainslie, Chow, Myers, Mantas -- consistent with normal "
        "ward casework, not on its own surprising."
    ),
    "manulife ontario property portfolio": (
        "75-81 Billy Bishop Way (Appeal Report). 3 registrants (2 consultants + 1 "
        "in-house exec) each independently logged exactly 1 contact to Josh Matlow, "
        "all on the SAME day, 2022-11-17. A same-day, multi-registrant contact to "
        "one office is a distinctive pattern worth a second look even though the "
        "total volume (3) is small."
    ),
    "2724471 ontario": (
        "3 Swift Drive. Tristan Downe-Dewdney again (see microbjo properties and "
        "crestview investment) -- 5 contacts tied to this subject matter across 4 "
        "councillors (Matlow, Moise, Carroll, Morley x2) in a tight "
        "Jan 29-Feb 1, 2024 window."
    ),
    "slh lakeshore": (
        "685 Lake Shore Blvd E (Appeal Report). 2 registrants, zero lobbied-office "
        "contacts tied to either subject matter -- thin."
    ),
    "12723638 canada": (
        "1 Broadlands Blvd. One registrant (Christian Chan, planner), zero "
        "lobbied-office contacts tied to this subject matter."
    ),
    "brad jay investments": (
        "1911 Finch Ave West -- the Jane Finch Mall redevelopment. 4 registrants; "
        "only the in-house registrant (Jay Feldman, President) shows any "
        "same-subject-matter contact: a single contact to Anthony Perruzza, "
        "July 2023. This is a large, publicly-watched redevelopment; the low "
        "same-subject-matter contact count here likely reflects that most real "
        "engagement on a project this size runs through planning-committee/public-"
        "consultation channels the lobbyist registry doesn't capture, not that no "
        "engagement happened."
    ),
    "crestview investment": (
        "245 Eglinton Ave E. The standout of the 14: Tristan Downe-Dewdney (same "
        "registrant as microbjo properties and 2724471 ontario above) logged 42 "
        "contacts to a single councillor, Rachel Chernos Lin, tied to this exact "
        "subject matter (SM36776), spanning July 17, 2025 to July 16, 2026 -- a "
        "full year of sustained, repeated contact to one office about one "
        "property. Two more registrants (one consultant, one in-house President/"
        "CEO) each separately logged 2 more contacts to the same councillor around "
        "the same subject matter, Aug 6, 2025. The highest same-subject-matter "
        "contact volume to a single office found among these 14 -- but Downe-"
        "Dewdney appears on 3 of the 14, suggesting he's simply an extremely "
        "active development lobbyist generally (1,174 total contacts, 24 offices) "
        "rather than each instance being independently notable on its own."
    ),
    "toronto community housing": (
        "325 Gerrard St E -- Regent Park Phases 4 and 5. The outlier of the 14: "
        "Toronto Community Housing Corporation is a public, city-owned arm's-"
        "length agency, not a private developer. 12 registrants across many "
        "subject matters spanning 2018-2023, overwhelmingly typed 'subsidiary_"
        "company'/'other' rather than 'client' -- these are hired consultants on "
        "a long-running public redevelopment, not evidence of a private "
        "beneficiary buying access. Two registrants (Karakusevic, Miller) show 1 "
        "contact each to McKelvie and Moise on the same day, March 2023. "
        "Structurally different in kind from the other 13 -- flagged explicitly "
        "so it isn't read as a private-developer finding."
    ),
}


def load(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    entities = {r["entity_id"]: r for r in load(INTERIM / "kg_entities.csv")}
    edges = load(INTERIM / "kg_edges.csv")
    members = {f"member:{r['member_id']}": r for r in load(INTERIM / "member_terms.csv")}

    role_edges = [e for e in edges if e["edge_type"] == "role__owner"]
    lobby_edges = [e for e in edges if e["edge_type"].startswith("lobbies_for__") or e["edge_type"] == "represents"]
    lobbied_office_by_registrant = {}
    for e in edges:
        if e["edge_type"] == "lobbied_office":
            lobbied_office_by_registrant.setdefault(e["source_id"], []).append(e)

    org_by_key = {e["match_key"]: e for e in entities.values() if e["entity_type"] == "org"}

    rows_out = []
    for key in ORG_MATCH_KEYS:
        org = org_by_key.get(key)
        if org is None:
            print(f"WARNING: no org entity found for match_key {key!r}")
            continue
        org_id = org["entity_id"]

        owner_of = [e for e in role_edges if e["source_id"] == org_id]
        item_summaries = []
        for e in owner_of:
            item = entities.get(e["target_id"], {})
            item_summaries.append(f"{e['target_id'].replace('devapp:', '')}: {item.get('display_name', '?')}")

        reps = [e for e in lobby_edges if e["target_id"] == org_id]
        registrant_summaries = []
        for e in reps:
            registrant = entities.get(e["source_id"], {})
            sm_match = SM_RE.search(e["basis"])
            sm = sm_match.group(1) if sm_match else None
            offs = [oe for oe in lobbied_office_by_registrant.get(registrant.get("entity_id"), [])
                    if sm and oe["basis"].startswith(sm)]
            office_counts = {}
            for oe in offs:
                name = members.get(oe["target_id"], {}).get("member_name", "?")
                office_counts[name] = office_counts.get(name, 0) + 1
            contacts_str = ", ".join(f"{n}x{c}" for n, c in office_counts.items()) if office_counts else "none"
            registrant_summaries.append(
                f"{registrant.get('display_name', '?')} ({registrant.get('notes', '')}, {e['edge_type']}) "
                f"same-SM contacts: {contacts_str}"
            )

        rows_out.append({
            "org_name": org["display_name"],
            "owner_of_items": "; ".join(item_summaries),
            "registrants_and_same_subject_matter_contacts": " | ".join(registrant_summaries),
            "llm_first_pass_note": NOTES.get(key, ""),
            "reviewer_verdict": "",
            "reviewer_note": "",
        })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)
    print(f"Wrote {len(rows_out)} rows -> {OUT_PATH}")


if __name__ == "__main__":
    main()
