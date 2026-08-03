"""
Build member_terms.csv: councillor/mayor <-> ward <-> office <-> date range,
plus which contributions.csv `election` slice funded their current seat.

Per docs/05-pipeline.md: "Councillor<->ward is not static across 2022-2026.
Model this as member_terms(member_id, ward, office, start_date, end_date) and
join votes to it by date. A flat lookup dict will silently misattribute votes."

Source of the roster and by-election facts: this is NOT pulled from an API --
there is no dataset that states "who currently holds this seat." It was
verified live via web search/fetch against Wikipedia's
"Toronto City Council 2022-2026" page and the City of Toronto's official
"Members of Council" page (both fetched 2026-08-02, cross-agreeing on every
seat), and cross-checked against the four by-election dates already verified
independently in Phase 0 (docs/08, 2026-08-02 "By-elections require separate
contribution exports") -- all four dates match exactly across both
verification passes. Term start Nov 15, 2022 verified via City of Toronto
news release ("First Meeting of the 2022-2026 Toronto City Council term").

If this script is rerun in a later session, re-verify the roster live before
trusting it -- by-elections can happen at any time and this file is a
snapshot, not a live query.
"""
import csv
from pathlib import Path

OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "interim" / "member_terms.csv"

TERM_START = "2022-11-15"
GENERAL = "2022 Municipal Election"

# (member_id, member_name (First Last), efd_candidate_name ("Last, First" as it
#  appears in contributions.csv `candidate`), ward_number, ward_name, office,
#  start_date, end_date, predecessor_name, predecessor_departure_reason,
#  source_election, notes)
ROWS = [
    # --- Mayor ---
    ("tory_john", "John Tory", "Tory, John", 0, "Mayor (city-wide)", "Mayor",
     TERM_START, "2023-02-17", None, None, GENERAL,
     "Resigned 2023-02-17."),
    ("chow_olivia", "Olivia Chow", "Chow, Olivia", 0, "Mayor (city-wide)", "Mayor",
     "2023-06-26", None, "John Tory", "Resigned 2023-02-17",
     "2023 Mayoral By-Election", "Currently sitting."),

    # --- Wards 1-14, 16-19, 21-24: unchanged since the 2022 general ---
    ("crisanti_vincent", "Vincent Crisanti", "Crisanti, Vincent", 1, "Etobicoke North", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("holyday_stephen", "Stephen Holyday", "Holyday, Stephen", 2, "Etobicoke Centre", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("morley_amber", "Amber Morley", "Morley, Amber", 3, "Etobicoke-Lakeshore", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("perks_gord", "Gord Perks", "Perks, Gord", 4, "Parkdale-High Park", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("nunziata_frances", "Frances Nunziata", "Nunziata, Frances", 5, "York South-Weston", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting. Also Council Speaker."),
    ("pasternak_james", "James Pasternak", "Pasternak, James", 6, "York Centre", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("perruzza_anthony", "Anthony Perruzza", "Perruzza, Anthony", 7, "Humber River-Black Creek", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("colle_mike", "Mike Colle", "Colle, Mike", 8, "Eglinton-Lawrence", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("bravo_alejandra", "Alejandra Bravo", "Bravo, Alejandra", 9, "Davenport", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("malik_ausma", "Ausma Malik", "Malik, Ausma", 10, "Spadina-Fort York", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting. Also Deputy Mayor."),
    ("saxe_dianne", "Dianne Saxe", "Saxe, Dianne", 11, "University-Rosedale", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("matlow_josh", "Josh Matlow", "Matlow, Josh", 12, "Toronto-St. Paul's", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("moise_chris", "Chris Moise", "Moise, Chris", 13, "Toronto Centre", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("fletcher_paula", "Paula Fletcher", "Fletcher, Paula", 14, "Toronto-Danforth", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("burnside_jon", "Jon Burnside", "Burnside, Jon", 16, "Don Valley East", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("carroll_shelley", "Shelley Carroll", "Carroll, Shelley", 17, "Don Valley North", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("cheng_lily", "Lily Cheng", "Cheng, Lily", 18, "Willowdale", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("bradford_brad", "Brad Bradford", "Bradford, Brad", 19, "Beaches-East York", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("thompson_michael", "Michael Thompson", "Thompson, Michael", 21, "Scarborough Centre", "Councillor",
     TERM_START, None, None, None, GENERAL,
     "Currently sitting. RESOLVED 2026-08-02: was missing from the EFD bulk "
     "export entirely (confirmed a genuine gap, not a spelling issue). User "
     "supplied his filed Form 4 financial statement (PDF) directly; 120 "
     "contribution rows transcribed and checksummed against the form's own "
     "declared Schedule 1 Part III total ($96,500.00, exact match) via "
     "pipeline/transform/thompson_form4_transcription.py, then merged into "
     "contributions.csv via merge_thompson_form4.py. Source PDF archived at "
     "data/raw/efd_contributions/2022_thompson_ward21_form4.pdf. His donor "
     "data source is NOT the EFD system for this reason -- flagged in case "
     "the EFD export gap is ever explained (e.g. a future site fix) and the "
     "two sources need reconciling to avoid double-counting."),
    ("mantas_nick", "Nick Mantas", "Mantas, Nick", 22, "Scarborough-Agincourt", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("myers_jamaal", "Jamaal Myers", "Myers, Jamaal", 23, "Scarborough North", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),
    ("ainslie_paul", "Paul Ainslie", "Ainslie, Paul", 24, "Scarborough-Guildwood", "Councillor",
     TERM_START, None, None, None, GENERAL, "Currently sitting."),

    # --- Ward 15: Jaye Robinson (2022) -> died 2024-05-16 -> Rachel Chernos Lin (by-election 2024-11-04) ---
    ("robinson_jaye", "Jaye Robinson", "Robinson, Jaye", 15, "Don Valley West", "Councillor",
     TERM_START, "2024-05-16", None, None, GENERAL,
     "Died in office 2024-05-16. Not currently sitting; retained for historical vote/donor analysis only."),
    ("chernoslin_rachel", "Rachel Chernos Lin", "Chernos Lin, Rachel", 15, "Don Valley West", "Councillor",
     "2024-11-04", None, "Jaye Robinson", "Died in office 2024-05-16",
     "2024 Ward 15 By-Election",
     "Currently sitting. NOTE: also appears in contributions.csv 2022 Municipal "
     "Election as a Toronto District School Board trustee candidate (Ward 11 "
     "TDSB), not a council candidate -- that row is NOT part of her council "
     "donor base and is excluded by the source_election rule."),

    # --- Ward 20: Gary Crawford (2022) -> resigned 2023-07-26 -> Parthi Kandavel (by-election 2023-11-30) ---
    ("crawford_gary", "Gary Crawford", "Crawford, Gary", 20, "Scarborough Southwest", "Councillor",
     TERM_START, "2023-07-26", None, None, GENERAL,
     "Resigned 2023-07-26. Not currently sitting; retained for historical vote/donor analysis only."),
    ("kandavel_parthi", "Parthi Kandavel", "Kandavel, Parthi", 20, "Scarborough Southwest", "Councillor",
     "2023-11-30", None, "Gary Crawford", "Resigned 2023-07-26",
     "2023 Ward 20 By-Election",
     "Currently sitting. EDGE CASE: Kandavel also ran for this same seat in "
     "the 2022 general election and LOST to Crawford -- contributions.csv has "
     "a 'Kandavel, Parthi' / 'Councillor' / ward 20 / '2022 Municipal Election' "
     "slice from that losing campaign. Per the mechanical rule 'donor base = "
     "the campaign that won the seat this member currently holds,' the 2022 "
     "rows are excluded from the main specification. Flagged as a candidate "
     "for a sensitivity check in docs/04 Phase 3 (does including his failed "
     "2022 campaign's donors change anything for his row), not resolved here."),

    # --- Ward 25: Jennifer McKelvie (2022) -> resigned 2025-05-09 -> Neethan Shan (by-election 2025-09-29) ---
    ("mckelvie_jennifer", "Jennifer McKelvie", "McKelvie, Jennifer", 25, "Scarborough-Rouge Park", "Councillor",
     TERM_START, "2025-05-09", None, None, GENERAL,
     "Resigned 2025-05-09. Not currently sitting; retained for historical vote/donor analysis only."),
    ("shan_neethan", "Neethan Shan", "Shan, Neethan", 25, "Scarborough-Rouge Park", "Councillor",
     "2025-09-29", None, "Jennifer McKelvie", "Resigned 2025-05-09",
     "2025 Ward 25 By-Election",
     "Currently sitting. NOTE: also appears in contributions.csv 2022 Municipal "
     "Election as a Toronto District School Board trustee candidate (Ward 17 "
     "TDSB), not a council candidate -- that row is NOT part of his council "
     "donor base and is excluded by the source_election rule."),
]

FIELDS = [
    "member_id", "member_name", "efd_candidate_name", "ward_number", "ward_name",
    "office", "start_date", "end_date", "predecessor_name",
    "predecessor_departure_reason", "source_election", "notes",
]


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        for row in ROWS:
            writer.writerow(["" if v is None else v for v in row])
    print(f"Wrote {len(ROWS)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
