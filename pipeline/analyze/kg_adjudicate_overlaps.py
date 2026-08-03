"""
Manual adjudication pass, per docs/02's "Manual adjudication" section, applied
to the knowledge graph's 8 corroborated (name + shared postal code)
registrant<->same-member-donor overlaps from kg_summary.py.

This is the LLM first-cut docs/02 describes ("An LLM pass can do first-cut
classification cheaply. It must produce the basis string for every call...
Any LLM-assigned label above a materiality threshold gets human review
before publication.") -- reviewer_verdict/reviewer_note are left blank for
the user's own read, same pattern as audit/donor_review.csv.

Important limit stated plainly: a matching name + matching postal code is
strong circumstantial evidence, not proof of identity (could in principle
be two different people at the same address -- family, roommates, a shared
office building). None of these 8 have been checked against any source
outside this repo's own data.

Output: audit/kg_lobbyist_donor_overlap_review.csv
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
OUT_PATH = ROOT / "audit" / "kg_lobbyist_donor_overlap_review.csv"

PAIRS = [
    ("bradford_brad", "42589C", "campbell, john", "M9A3Y3"),
    ("bradford_brad", "18935S", "scrivener, paul", "M2L2N9"),
    ("thompson_michael", "43327S", "sarick, madeleine", "M3C3E9"),
    ("matlow_josh", "54801C", "mihevc, joe", "M6C2W2"),
    ("matlow_josh", "37069C", "milczyn, peter", "L5H1G6"),
    ("matlow_josh", "50785S", "larjani, sherry", "M5A1V2"),
    ("saxe_dianne", "51898S", "quinn, francisca", "M4W1V3"),
    ("perruzza_anthony", "54801C", "mihevc, joe", "M6C2W2"),
]

# LLM first-cut notes, written by hand from the pulled evidence (this is a
# small, fixed set of 8 -- not worth a generalized scoring function).
NOTES = {
    ("bradford_brad", "42589C"): (
        "Same name + same single-address-style postal code (2 Cranleigh Court, "
        "a house, not a large building -- tighter corroboration than a typical "
        "Signal-1 cluster). Registrant is a Consultant-type government-relations "
        "professional (Sutherland Corp) with a large, mostly dev-related client "
        "book. $500 donation was during the 2022 campaign, before Bradford held "
        "office; the 3 lobbying contacts followed in 2023-2024, after he was "
        "sitting. Ordinary, legal professional-lobbyist conduct -- not evidence "
        "of impropriety on its own, but a real, documented pre-election-support "
        "-> post-election-access sequence."
    ),
    ("bradford_brad", "18935S"): (
        "Same name + same house-style postal code (28 Bannatyne Drive). Note for "
        "precision: the $250 donation went to Bradford's LOSING 2023 mayoral "
        "bid, not his council campaign -- still money to the same person who "
        "now holds the Ward 19 seat, but that distinction matters if this is "
        "written up. Registrant represents 'Toronto Industry Network' (by-law/ "
        "economic development/environment) -- broader industry-association "
        "lobbying, not specifically real-estate development. 8 emails over "
        "2023-2025, ordinary correspondence volume."
    ),
    ("thompson_michael", "43327S"): (
        "Same name + same postal code. Registrant is 'owner' of Samuel Sarick "
        "Limited / Graduate Investments Limited (real-estate-sounding company "
        "names) on a Planning-and-Development subject matter. But the lobbying "
        "evidence is thin: a single email, 2025-12-12, more than 3 years after "
        "the 2022 donation. Identity match is solid; the 'access' pattern is "
        "not -- one email is closer to ordinary constituent correspondence "
        "than a lobbying relationship."
    ),
    ("matlow_josh", "54801C"): (
        "Same name + same house-style postal code (8 Humewood Dr). Registrant "
        "is 'Principal' of a planning/development consultancy (Mihevc "
        "Consulting and Mediation Ltd) with ~25 subject-matter filings, "
        "overwhelmingly Planning and Development / zoning, for major "
        "developer clients (Castlepoint, Fitzrovia, QuadReal, Reserve "
        "Properties, and more). $500 went to Matlow's losing 2023 mayoral "
        "bid. 3 lobbying contacts to Matlow's council office span 2024-2026 "
        "-- a real, ongoing, multi-year professional relationship, not a "
        "one-off. Also see the perruzza_anthony/54801C row below: the same "
        "person donated to two different sitting councillors' mayoral bids "
        "and has active lobbying relationships with both offices."
    ),
    ("matlow_josh", "37069C"): (
        "Same name + same postal code -- notably a Mississauga (out-of-city) "
        "address, which is a tighter coincidence bar than a Toronto postal "
        "code shared by many donors. Registrant is 'Principal' at PM "
        "Strategies Inc with 40+ dev-related filings for major developers "
        "(Concord Adex/Concord Pacific, TRIDEL, Dunpar, Vandyk, and more) -- "
        "the largest, most dev-concentrated client book of the 8. $1,500 "
        "total (two contributions) to Matlow's losing 2023 mayoral bid. "
        "8 lobbying contacts to Matlow's council office spanning 2023-2026, "
        "multiple methods (meetings, calls, emails) -- sustained access."
    ),
    ("matlow_josh", "50785S"): (
        "Same name + same postal code. Registrant is In-house Managing "
        "Director at 'Spotlight Development' (a development company). "
        "Sequence is notable and stated precisely: 5 lobbying contacts to "
        "Matlow's office and two named staffers, all within Oct 24-27, 2023 "
        "(one active week), then a $500 donation on 2023-11-03 -- about a "
        "week after the last contact. Lobby-then-donate order, the reverse "
        "of most of the other 7 rows here."
    ),
    ("saxe_dianne", "51898S"): (
        "Same name + same postal code. Registrant is In-house Director at "
        "'Prince Arthur Real Estate Corporation.' The $1,200 donation to Saxe "
        "in 2022 was AT the councillor contribution limit -- the largest "
        "dollar figure of the 8 relative to the applicable limit. Lobbying "
        "evidence is thin: one email, 2025-01-29, over two years after the "
        "donation, on a heritage/planning matter."
    ),
    ("perruzza_anthony", "54801C"): (
        "Same registrant as matlow_josh/54801C above (Joe Mihevc). $250 to "
        "Perruzza's losing 2023 mayoral bid. 2 lobbying contacts to "
        "Perruzza's council office, 2025-2026. See the Matlow row for the "
        "fuller professional profile -- this is the same person's second "
        "sitting-councillor relationship."
    ),
}


def load(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    subj = load(INTERIM / "lobbyist_subject_matters.csv")
    donors = load(INTERIM / "donors.csv")
    edges = load(INTERIM / "kg_edges.csv")
    members = {m["member_id"]: m for m in load(INTERIM / "member_terms.csv")}

    rows_out = []
    for member_id, regnum, donor_key, postal in PAIRS:
        m = members[member_id]
        reg_rows = [r for r in subj if r["registrant_RegistrationNUmber"] == regnum]
        r0 = reg_rows[0]
        d_rows = [r for r in donors if r["name_norm"].strip() == donor_key and r["postal_code"] == postal]
        lobby_edges = [
            e for e in edges
            if e["edge_type"] == "lobbied_office"
            and e["source_id"] == f"reg:{regnum}"
            and e["target_id"] == f"member:{member_id}"
        ]
        dates = sorted(e["date"] for e in lobby_edges if e["date"])

        rows_out.append({
            "member_name": m["member_name"],
            "registrant_name": f"{r0['registrant_FirstName']} {r0['registrant_LastName']}",
            "registrant_type": r0["registrant_Type"],
            "registrant_position": r0["registrant_PositionTitle"],
            "registrant_firm_or_client_count": len(reg_rows),
            "shared_postal_code": postal,
            "donor_total_amount_net": round(sum(float(r["amount_net"]) for r in d_rows), 2),
            "donor_contributions": "; ".join(
                f"{r['date_received']} ${r['amount_net']} -> {r['candidate']} ({r['office']})" for r in d_rows
            ),
            "lobbying_contacts_to_this_member": len(lobby_edges),
            "lobbying_date_range": f"{dates[0]} to {dates[-1]}" if dates else "",
            "llm_first_pass_note": NOTES[(member_id, regnum)],
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
