"""
One-off transcription of Michael Thompson's Form 4 financial statement
(user-provided PDF, filed with City Clerk 2023-03-29, campaign period
2022-05-30 to 2023-01-03), Schedule 1 Part III Table 3: monetary
contributions from individuals other than candidate/spouse exceeding $100.

Why this exists: Thompson has zero rows in the EFD bulk export
(data/interim/contributions.csv) under any spelling -- confirmed and logged
in docs/08-decision-log.md (2026-08-02). The user supplied his actual filed
Form 4 as a PDF. This script transcribes Table 3 and validates the
transcription against the form's own declared subtotal ($96,500.00, line 1B
of Schedule 1) before it is trusted -- a checksum on hand-transcribed OCR
output, not a guess.

Excluded from this table by the form's own structure: the $200 in-kind
contribution from the candidate himself (Part II, not from another
individual -- would violate "every donor is a person other than the
candidate" framing if included as a third-party donor), and the aggregate
$250 in un-itemized contributions of $100-or-less per contributor (no
per-row detail given on the form for these, so they cannot be added as
individual donor rows -- logged as a known undercount, same treatment as
any other bulk aggregate).
"""
import csv
from pathlib import Path

OUT_PATH = Path(__file__).resolve().parents[2] / "data" / "interim" / "thompson_form4_contributions.csv"

# (last, first, street_address, city, postal_code, date_received, amount)
ROWS = [
    ("ABOOSAIDI", "ARYA", "61 TRUMAN Rd", "TORONTO", "M2L 2L7", "2022-10-11", 1200.00),
    ("BANSAL", "SHIV", "33 MUMBERSON Crt", "MARKHAM", "L6C 1Y4", "2022-10-11", 500.00),
    ("BESNER", "JAMIE", "114 MEADOWBANK Rd", "TORONTO", "M9B 5E3", "2022-10-11", 500.00),
    ("BISHOP", "STEVEN", "1037 STREAMBANK Dr", "MISSISSAUGA", "L5H 3W7", "2022-12-30", 500.00),
    ("BORDONALI", "DANIEL", "10 MCMAHON COURT Crt", "RICHMOND HILL", "L4E 0T6", "2022-10-11", 500.00),
    ("BOYADJIAN", "HOVIC", "485 STEPHANIE Blvd", "WOODBRIDGE", "L3L 0A7", "2022-10-11", 500.00),
    ("BROWN", "MARLA", "28 DUNLOE Rd", "TORONTO", "M4V 2W5", "2022-08-30", 1200.00),
    ("BROWN", "PAUL", "442 MELROSE Ave", "NORTH YORK", "M5M 1Z9", "2022-08-30", 600.00),
    ("CAMPBELL", "BARRY", "1 ROXBOROUGH St E 502", "TORONTO", "M4W 1V5", "2022-08-03", 500.00),
    ("CHAMPSEE SHAH", "PUSHPLATA", "21 SWIFTDALE Pl", "TORONTO", "M3B 1M3", "2022-10-11", 500.00),
    ("CHAMPSEE SHAH", "PUSHPLATA", "21 SWIFTDALE Pl", "TORONTO", "M3B 1M3", "2022-10-11", 700.00),
    ("CHEN", "LUJIA", "23 SHEPPARD Ave E 2905", "NORTH YORK", "M2N 0C8", "2022-07-13", 1000.00),
    ("CHEONG CHEUNG", "DR. CHI", "7 DUNDAS Sq 300", "TORONTO", "M5B 1B5", "2022-10-11", 1200.00),
    ("CHERRY", "JOHN", "12 COUNTRY ESTATES Dr", "MARKHAM", "L6C 1A4", "2022-10-11", 500.00),
    ("CHIN", "RYAN M.", "1527 CONCESSION Rd E", "MILLGROVE", "L0R 1V0", "2023-01-03", 500.00),
    ("CHRISTOFORIDIS", "JOHN", "27 ELLINGTON Dr", "SCARBOROUGH", "M1R 3Z7", "2022-10-11", 500.00),
    ("D'ONOFRIO", "GUY", "530 ST. CLAIR Ave W 1808", "TORONTO", "M6C 0A2", "2022-10-11", 500.00),
    ("DAWANI", "MURLIDHAR", "2238 HIGHWOOD Crt", "OAKVILLE", "L6M 4Z9", "2023-01-03", 500.00),
    ("DIAMOND", "STEPHEN", "68 WARREN Rd", "TORONTO", "M4V 2R5", "2022-07-13", 300.00),
    ("DOMINELLI", "FRED", "45 FIMA Cres", "ETOBICOKE", "M8W 3R1", "2022-10-11", 500.00),
    ("DOWNE-DEWDNEY", "TRISTAN", "222 THE ESPLANADE 409", "TORONTO", "M5A 4M8", "2022-10-11", 500.00),
    ("DOYLE", "JOHN PAUL", "110 CRESCENT Rd", "TORONTO", "M4W 1T5", "2022-07-13", 500.00),
    ("DRENNAN", "ANGELA", "17 ALDERDALE Crt", "TORONTO", "M3B 2H8", "2022-10-11", 500.00),
    ("DUNCAN", "ANDREW", "160 SHERWOOD Ave", "TORONTO", "M4P 2A8", "2022-10-11", 500.00),
    ("FEELEY", "MARY-JANE", "18 ARGUS Crt", "TORONTO", "M2J 5G8", "2022-10-11", 1000.00),
    ("FELDBERG", "JEFFREY", "175 SPARKS Ave", "TORONTO", "M2H 2S5", "2022-08-30", 1200.00),
    ("FELDBERG", "VICTORIA", "35 SANDRINGHAM Dr", "TORONTO", "M5M 3G4", "2022-08-30", 1200.00),
    ("FRANKFORT", "GEORGE", "51 JACKES Ave 103", "TORONTO", "M4T 1E2", "2022-12-30", 500.00),
    ("GAJIWALA", "HITESH", "531 BUR OAK Ave", "MARKHAM", "L6C 2S5", "2022-08-30", 1200.00),
    ("GERELIOUK", "NADIA", "1207 ROYAL YORK Rd", "TORONTO", "M9A 4B5", "2022-10-11", 500.00),
    ("GOLDHAR", "MITCHELL", "3200 HIGHWAY 7", "VAUGHAN", "L4K 5Z5", "2023-01-03", 300.00),
    ("GOLDMAN", "MURRAY", "1 STRATHEARN Blvd", "TORONTO", "M5P 1S6", "2022-07-13", 1200.00),
    ("GOLDRING", "BLAKE", "63 ALEXANDRA Blvd", "TORONTO", "M4R 1M1", "2022-10-11", 1200.00),
    ("GRANOVSKY", "IRVING", "29 OLD COLONY Rd", "TORONTO", "M2L 2J7", "2022-10-11", 500.00),
    ("GREEN", "CARY", "104 BIDEWELL Ave", "TORONTO", "M3H 1J9", "2023-01-03", 1200.00),
    ("GUMIENK", "KONRAD", "10 FIRST St", "ETOBICOKE", "M8V 2W9", "2022-10-11", 700.00),
    ("GUPTA", "DR. SUNJAY", "85 FIFESHIRE Rd", "TORONTO", "M2L 2G9", "2022-10-11", 1200.00),
    ("GUPTA", "NARINDER", "38 BECKENRIDGE Dr", "MARKHAM", "L3S 2V9", "2022-10-11", 500.00),
    ("GUPTA", "RAY", "130 WOODVIEW Dr", "PICKERING", "L1V 1L2", "2022-10-11", 1200.00),
    ("GUPTA", "SANDEEP", "183 WELLINGTON St W 3501", "TORONTO", "M5V 0A1", "2022-10-11", 1200.00),
    ("HAIG LAPOYAN", "VAHN", "30 FIFESHIRE Rd", "TORONTO", "M2L 2G6", "2022-10-11", 1200.00),
    ("HALSTEAD", "JOSEPH", "67 CHEESEMAN Dr", "MARKHAM", "L3R 3G3", "2022-10-11", 500.00),
    ("IACOBELLI", "LUIGI", "92 CLUB HOUSE Rd", "WOODBRIDGE", "L4L 2W2", "2022-07-13", 1200.00),
    ("ISAKOW", "BRUCE", "30 LANGTRY Pl", "THORNHILL", "L4J 8K8", "2022-10-11", 1200.00),
    ("JAIN", "DR. MAHENDRA", "65 HILL Cres", "TORONTO", "M1M 1J3", "2022-10-11", 500.00),
    ("JEANRIE", "ANDREW", "89 RYKERT Cres", "TORONTO", "M4G 2T4", "2022-10-11", 500.00),
    ("KANJI", "ALEEM", "1403 LONDONDERRY Blvd", "MISSISSAUGA", "L5E 2S2", "2022-10-11", 500.00),
    ("KEELEY", "ROGER", "38 ALBERT St", "MARKHAM", "L3P 2T5", "2022-10-11", 500.00),
    ("KIRBY", "CAMERON", "910 DUNCANNON Dr", "PICKERING", "L1X 2M3", "2022-12-30", 600.00),
    ("KORWIN-KUCZYNSKI", "CHRIS", "2285 LAKESHORE Blvd W 2113", "TORONTO", "M8V 3X9", "2022-07-13", 300.00),
    ("KRAKOWSKI", "CHRISTINA", "147 TAYLOR Dr", "BARRIE", "L4N 8K9", "2022-12-30", 500.00),
    ("KRANTMAN", "YURIY", "10 TANGREEN Crt 2408", "TORONTO", "M2M 4B9", "2022-08-30", 1200.00),
    ("LAMANNA", "CHRISTIAN", "369 RIMROCK Rd", "TORONTO", "M3J 3G2", "2022-07-13", 1200.00),
    ("LAZO", "WALEUSKA", "48 SANDRINGHAM Dr", "TORONTO", "M5M 3G3", "2022-08-30", 1200.00),
    ("LEVY", "BRYAN", "11 CURITY Ave 1", "TORONTO", "M4B 1X4", "2022-12-30", 1000.00),
    ("LI", "ZHONGBIN", "43 GERDEN Dr", "RICHMOND HILL", "L4S 0H1", "2022-10-11", 1200.00),
    ("LIU", "ZHI GAO", "23 SHEPPARD Ave E 2905", "NORTH YORK", "M2N 0C8", "2022-07-13", 1000.00),
    ("LIVEY", "JOHN", "56 MEADOWBROOK Lane", "MARKHAM", "L3R 2C6", "2022-10-11", 1000.00),
    ("LONG", "JOHN", "324 CHERRY St", "TORONTO", "M5A 3L1", "2022-10-11", 1200.00),
    ("LORUSSO", "CARL", "175 CUMBERLAND St", "TORONTO", "M5R 3M9", "2022-10-11", 750.00),
    ("MACKINNON", "CAMERON", "15 VANITY Crt", "DON MILLS", "M3A 1W9", "2022-10-11", 500.00),
    ("MAGAR", "ALFRED", "28 ILFRACOMBE Cres", "TORONTO", "M1R 3R8", "2022-07-13", 1200.00),
    ("MAK", "EDWARD", "22 STOTTS Cres", "MARKHAM", "L6E 1T4", "2022-07-13", 1000.00),
    ("MALEK", "IQBAL", "44A ROSEMOUNT Dr", "TORONTO", "M1K 2W9", "2022-10-11", 500.00),
    ("MANDRONIS", "PETER", "99 MORBANK Dr", "SCARBOROUGH", "M1V 2M1", "2022-08-30", 1000.00),
    ("MANGARU", "DOULATRAM", "24 KENMARK Blvd", "SCARBOROUGH", "M1K 3N7", "2022-12-30", 500.00),
    ("MCKAIGUE", "ROSEMARY", "2764 13TH LINE RR#1", "GILFORD", "L0L 1R0", "2022-10-11", 500.00),
    ("MCKEOWN", "KEVIN", "369 RIMROCK Rd", "TORONTO", "M3J 3G2", "2022-07-13", 1200.00),
    ("MOLEDINA", "IQBAL", "9 HORNER Crt", "RICHMOND HILL", "L4B 3G6", "2022-10-11", 500.00),
    ("MONTESANO", "ELISE", "92 CLUB HOUSE Rd", "WOODBRIDGE", "L4L 2W2", "2022-07-13", 1200.00),
    ("MORAG RUSEN", "SOPHIE", "365 BEECH Ave", "TORONTO", "M4R 0C2", "2022-10-11", 500.00),
    ("MORROW", "MELISSA", "160 SHERWOOD Ave", "TORONTO", "M4P 2A8", "2022-10-11", 500.00),
    ("MORROW", "TANYA", "161 BRIDGELAND Ave", "TORONTO", "M6A 1Z1", "2022-10-11", 750.00),
    ("MU", "HUAIYI", "35 RIVIERA Dr 8", "MARKHAM", "L3R 8N4", "2022-08-03", 1000.00),
    ("VO", "LYLY N.", "55 ST. CLAIR Ave W 240", "TORONTO", "M4V 2Y7", "2022-10-11", 500.00),
    ("NTOULIS", "THEODORIS T", "44 GEDDINGTON Cres", "MARKHAM", "L6B 0M7", "2022-08-30", 1200.00),
    ("OREN", "MICHAEL", "28 REINER Rd", "TORONTO", "M3H 2L2", "2022-10-11", 500.00),
    ("PAGNIELLO", "PALMINA", "76 DEERFIELD Rd", "TORONTO", "M1K 4X3", "2022-08-30", 1200.00),
    ("PAGNIELLO", "SUE", "76 DEERFIELD Rd", "TORONTO", "M1K 4X3", "2022-08-30", 1200.00),
    ("PAPAJANI", "DRITAN", "79 NORMAN Dr", "KING CITY", "L7B 1J2", "2022-08-30", 1200.00),
    ("PAPAJANI", "ROLAND", "44 CHARLES St", "KING CITY", "L7B 1J2", "2022-08-30", 1200.00),
    ("PAPPALARDO", "VICTOR", "38 SAINTFIELD Ave", "TORONTO", "M3C 2M6", "2022-12-30", 1000.00),
    ("PARK", "IN (JASON)", "250 YONGE St 230", "TORONTO", "M5B 2L7", "2022-10-11", 1000.00),
    ("PASK", "ANDREW", "1028 BEECHNUT Rd", "OAKVILLE", "L6J 7P4", "2023-01-03", 500.00),
    ("PELECH", "WALTER", "99 HARBOUR Sq 2208", "TORONTO", "M5J 2H2", "2022-12-30", 250.00),
    ("PELLEGRINI", "PAUL", "37 TREVI Crt", "WOODBRIDGE", "L4L 8S7", "2022-10-11", 500.00),
    ("PLIAMM", "DR. LEW", "2 CHAMPAGNE Dr A2", "TORONTO", "M3J 0K2", "2022-10-11", 500.00),
    ("PROCIUK", "OKSANA", "14 DONALBERT Rd", "TORONTO", "M9B 2E8", "2022-10-11", 500.00),
    ("REID", "NICOLE", "910 DUNCANNON Dr", "PICKERING", "L1X 2M3", "2022-12-30", 1200.00),
    ("REISMAN", "ROSE", "46 BAYVIEW Ridge", "TORONTO", "M2L 1E5", "2022-10-11", 1000.00),
    ("REN", "WANLIN", "35 RIVIERA Dr 8", "MARKHAM", "L3R 8N4", "2022-08-03", 1000.00),
    ("ROGOL", "OLENA", "10 TANGREEN Crt 2408", "TORONTO", "M2M 4B9", "2022-08-30", 1200.00),
    ("RUZGAR", "ALI", "8 FRIVICK Crt", "NORTH YORK", "M2M 3P6", "2022-10-11", 500.00),
    ("SARICK", "MADELEINE", "95 BARBER GREENE Rd 305", "TORONTO", "M3C 3E9", "2022-10-11", 500.00),
    ("SCOTT", "DEBORAH", "57 WOODLAWN Ave W", "TORONTO", "M4V 1G6", "2022-10-11", 500.00),
    ("SCOTT", "DEBORAH", "57 WOODLAWN Ave W", "TORONTO", "M4V 1G6", "2022-10-11", 500.00),
    ("SHAH", "MILAN", "23 AUTOMATIC Rd", "BRAMPTON", "L6S 4K6", "2022-10-11", 500.00),
    ("SHAH", "MILAN", "23 AUTOMATIC Rd", "BRAMPTON", "L6S 4K6", "2022-10-11", 700.00),
    ("SHAH", "SHASHIKANT", "615 SENECA HILL Dr", "NORTH YORK", "M2J 2W6", "2022-10-11", 350.00),
    ("SHETH", "SUNITA", "5149 FRYBROOK Crt", "MISSISSAUGA", "L5M 5A8", "2022-10-11", 500.00),
    ("SINGER", "DAVID", "369 RIMROCK Rd", "TORONTO", "M3J 3G2", "2022-07-13", 1200.00),
    ("SINGER", "MIGUEL", "42 ALEXANDRA Wood", "TORONTO", "M5N 2S1", "2022-07-13", 1200.00),
    ("SMITH", "MELANIA", "2139 LAWRENCE Ave E", "SCARBOROUGH", "M1R 3A4", "2022-10-11", 1200.00),
    ("SMITH", "STEVE", "2139 LAWRENCE Ave E", "SCARBOROUGH", "M1R 3A4", "2022-10-11", 1200.00),
    ("SZETO", "ALFRED", "191 GREYABBEY Trl", "SCARBOROUGH", "M1E 1W2", "2022-12-30", 300.00),
    ("SZPINDEL", "ALON", "34 OTTER Cres", "TORONTO", "M5N 2W4", "2022-10-11", 1200.00),
    ("TANNOUS", "ALAA", "2 CHAMPAGNE Dr Unit A1", "TORONTO", "M3G 0K2", "2022-10-11", 500.00),
    ("THAVARATNASINGHAM", "RAJ", "36 PILOT St", "SCARBOROUGH", "M1E 2C4", "2022-10-11", 200.00),
    ("TSAKALOS", "JIM", "125 MILNER Ave", "TORONTO", "M1S 3R1", "2022-10-11", 500.00),
    ("TSEMENTZIS", "CHRISTOS", "31 ROTHWELL Rd", "SCARBOROUGH", "M1R 4K6", "2022-08-30", 1200.00),
    ("WAKS", "JAY", "11 COSMIC Dr", "DON MILLS", "M3B 3L5", "2022-10-11", 1200.00),
    ("WALROND", "ELORA ODESSA", "5288 BETHESDA Rd", "STOUFFVILLE", "L4A 3A2", "2022-10-11", 1000.00),
    ("WEISBROD", "MAXWELL", "138 LATIMER Ave", "TORONTO", "M5N 2M2", "2022-07-13", 1200.00),
    ("WONG", "ELEANOR", "360 BLOOR St E 905", "TORONTO", "M4W 3M3", "2022-10-11", 500.00),
    ("XIAN", "YING", "43 GERDEN Dr", "RICHMOND HILL", "L4S 0H1", "2022-10-11", 1200.00),
    ("XU", "LU", "65 LILIAN St 814", "TORONTO", "M4S 0A1", "2022-07-13", 1000.00),
    ("YAKUBOWICZ", "SIMON", "17 ALDERBROOK Dr", "DON MILLS", "M3B 1E3", "2022-10-11", 1000.00),
    ("YONG", "ZHENG", "1 UNKNOWN", "TORONTO", "M0M 0M0", "2022-07-13", 1000.00),
    ("ZAGDANSKI", "BARRY", "142 STRATHALLEN Blvd", "TORONTO", "M5N 1S7", "2022-07-13", 1200.00),
    ("ZIGART", "MELANIE", "65 REJANE Cres", "VAUGHAN", "L4J 5A2", "2022-08-30", 1200.00),
]

FORM_DECLARED_TOTAL = 96500.00  # Schedule 1, Part III, line 1B


def main():
    total = sum(r[6] for r in ROWS)
    print(f"Transcribed rows: {len(ROWS)}")
    print(f"Transcribed sum:  ${total:,.2f}")
    print(f"Form-declared 1B: ${FORM_DECLARED_TOTAL:,.2f}")
    diff = round(total - FORM_DECLARED_TOTAL, 2)
    print(f"Difference:       ${diff:,.2f}")
    if diff != 0:
        print("MISMATCH -- do not merge into contributions.csv until reconciled.")
        return

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["last_name", "first_name", "street_address", "city", "postal_code", "date_received", "amount"])
        for row in ROWS:
            writer.writerow(row)
    print(f"Checksum OK. Wrote {len(ROWS)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
