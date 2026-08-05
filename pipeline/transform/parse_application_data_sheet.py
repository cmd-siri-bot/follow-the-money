"""
Column-aware parser for the "Application Data Sheet" attachment found in
City of Toronto planning staff reports (data/raw/dev_application_pdfs/).
Feeds the "developers with influence over city hall" thread of the
lobbyist/donor knowledge graph -- see docs/08-decision-log.md, 2026-08-03
"Staff-report PDF route scoped and sampled."

Why word-position clustering, not extract_text()/extract_tables():
these Data Sheet tables have no ruled grid lines, so pdfplumber's
line-based table detector finds nothing (confirmed empty on every sampled
page), and plain extract_text() reads the page in stream order, which
interleaves the Applicant/Agent/Architect/Owner columns' names and
addresses into one jumbled block (e.g. "THE DONWAY BOUSFIELDS BDP. THE
DONWAY / EAST LIMITED INC. QUADRANGLE EAST LIMITED / ..."). Clustering
each word by its x0 coordinate against the header row's column
boundaries reconstructs the real columns.

Column sets vary (some reports have Applicant/Agent/Architect/Owner,
some only Applicant/Architect/Owner, "Owner" is sometimes "Owners") --
the header-detection step reads whatever columns are actually present
rather than assuming a fixed four.
"""
import re

HEADER_WORDS = {"Applicant", "Agent", "Architect", "Owner", "Owners"}
STOP_HEADERS = ["EXISTING PLANNING CONTROLS", "PROJECT INFORMATION"]
Y_TOLERANCE = 3  # points; words on the "same line" if top values are within this


def find_header_row(words):
    """Returns list of (label, x0) for the header row, sorted left to right,
    or None if no header row is found on this page."""
    candidates = [w for w in words if w["text"].rstrip(":") in HEADER_WORDS]
    if len(candidates) < 2:
        return None

    # group candidates by approximate top (line), take the line with the most hits
    lines = {}
    for w in candidates:
        key = round(w["top"] / Y_TOLERANCE)
        lines.setdefault(key, []).append(w)
    best_line = max(lines.values(), key=len)
    if len(best_line) < 2:
        return None

    best_line.sort(key=lambda w: w["x0"])
    return [(w["text"].rstrip(":"), w["x0"], w["top"], w["bottom"]) for w in best_line]


def extract_data_sheet_fields(page):
    """Returns dict {column_label: joined_text} or None if no header row found
    on this page. column_label is normalized: 'Owners' -> 'Owner'."""
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
    header = find_header_row(words)
    if header is None:
        return None

    header_bottom = max(h[3] for h in header)
    col_starts = [h[1] for h in header]
    col_labels = [("Owner" if h[0] == "Owners" else h[0]) for h in header]

    stop_top = None
    for w in words:
        if w["top"] > header_bottom and w["text"].rstrip(":") in ("EXISTING", "PROJECT"):
            stop_top = w["top"] if stop_top is None else min(stop_top, w["top"])

    # Safety bound independent of stop_top: real Applicant/Agent/Architect/
    # Owner values are a name plus a short address, never more than a
    # handful of lines. Some report layouts pack the planning-controls
    # table onto the same page with no text marker before it (e.g. no
    # literal "EXISTING"/"PROJECT" token precedes it), which would
    # otherwise let a column silently absorb the rest of the page.
    MAX_LINES_BELOW_HEADER = 8
    line_tops = sorted({round(w["top"] / Y_TOLERANCE) for w in words if w["top"] > header_bottom})
    if len(line_tops) > MAX_LINES_BELOW_HEADER:
        line_cap_top = line_tops[MAX_LINES_BELOW_HEADER] * Y_TOLERANCE
        stop_top = line_cap_top if stop_top is None else min(stop_top, line_cap_top)

    body_words = [
        w for w in words
        if w["top"] > header_bottom and (stop_top is None or w["top"] < stop_top)
    ]

    columns = {label: [] for label in col_labels}
    for w in body_words:
        # assign to the column whose start is the closest one at or before w's x0
        col_idx = 0
        for i, start in enumerate(col_starts):
            if w["x0"] >= start - 5:
                col_idx = i
        # group by line (top) for correct left-to-right, top-to-bottom order
        columns[col_labels[col_idx]].append((round(w["top"] / Y_TOLERANCE), w["x0"], w["text"]))

    result = {}
    for label, entries in columns.items():
        entries.sort(key=lambda e: (e[0], e[1]))
        lines = {}
        for line_key, _, text in entries:
            lines.setdefault(line_key, []).append(text)
        joined = " ".join(" ".join(lines[k]) for k in sorted(lines))
        result[label] = _truncate_at_planning_table_bleed(re.sub(r"\s+", " ", joined).strip())

    return result


# Some report layouts pack the Data Sheet and the planning-controls table
# onto the same page with no line break between them (e.g. "Kilmer
# Infrastructure Developments Official Plan Designation: ..." all on one
# reading line) -- geometry-based column splitting can't separate these,
# so truncate at the first recognizable planning-table field label
# regardless of where the line-count cap landed.
_BLEED_RE = re.compile(
    r"\s+(Official Plan Designation|Site Specific Provision|Zoning:|"
    r"Heritage Designation|Height Limit|Site Plan Control|Site Area|"
    r"Frontage|EXISTING PLANNING|PROJECT INFORMATION|"
    r"\b[YN]\b \(m\)|\bTotal\b|Building Data).*$"
)


def _truncate_at_planning_table_bleed(text):
    return _BLEED_RE.sub("", text).strip()


def find_and_parse_data_sheet(pdf):
    """Search all pages of an opened pdfplumber.PDF for the Application Data
    Sheet. Returns (page_number, fields_dict) or None."""
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if "Applicant" in text and ("Owner" in text or "Owners" in text):
            fields = extract_data_sheet_fields(page)
            if fields and fields.get("Applicant"):
                return i + 1, fields
    return None
