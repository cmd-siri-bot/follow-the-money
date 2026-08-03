# Decision Log

## 2026-08-02 — Repo root placement
Scaffolded the project directly inside `C:\Users\iamsi\toronto-2026-election` rather than creating a nested `follow-the-ask/` subfolder, since the working directory was empty and already dedicated to this project. No functional difference; naming only.

## 2026-08-02 — Vote record verified
Resource `55ead013-2331-4686-9895-9e8145b94189` confirmed live: 45,665 rows, `Agenda Item #` present as a stable join key, `Vote` values exactly `Yes`/`No`/`Absent`. No fallback to motion-text-only classification needed. See `phase0-findings.md` Step 2.

## 2026-08-02 — Lobbyist Registry has no datastore API
The `lobbyist-registry` package's primary resource is a ZIP (`94c1fe59-7247-4b92-b213-950f71e04aff`) with `datastore_active: False` — no `datastore_search` table. Extraction will need a download-and-parse step distinct from the other CKAN sources. Not a blocker, just a different code path in Phase 1.

## 2026-08-02 — Development Applications coverage confirmed
Resource `8907d8ed-c515-4ce9-b674-9f8c6eefcf0d`: 26,368 rows, `DATE_SUBMITTED` ranges 2008-01-04 to 2026-07-03, `WARD_NUMBER`/`WARD_NAME` present. Comfortably covers the 2022–2026 term.

## 2026-08-02 — EFD site requires a real browser; headless/scripted access is blocked
`app.toronto.ca` refuses HTTPS connections outright (port 443 connection refused, reproduced independently in the project owner's own browser). The real host is `secure.toronto.ca`; `app.toronto.ca` only serves plain HTTP and redirects. Direct scripted requests to `secure.toronto.ca` get a `403 Access Denied` from an apparent Akamai WAF layer. **Conclusion: any future automation of this site must run through a real browser session (e.g. Playwright with a normal user agent/session), not bare HTTP requests.**

## 2026-08-02 — EFD Step 3 resolved: full scope is a GO, scraping problem eliminated
The EFD contribution search page has an "Export" button that returns a bulk `.xls` of *every* matching row, and the "Candidate/Registrant Name" filter can be left blank. A blank-name search returned all 10,265 contribution records for the 2022 general election in a single file — well under the site's 55,000-row export cap. **This removes the need for ViewState-session-handling scraper code entirely for the contributions data.** Verdict per the decision tree in `docs/00-getting-started.md`: full scope (all 26 wards + mayor), not the reduced mayor+10-wards fallback.

## 2026-08-02 — Contribution data comes in postal code, not full address
The EFD export gives contributor postal code only, not street address (withheld under MFIPPA s.14, per the site's own disclosure). `STRATEGY.md` section 3.1 assumed full addresses would be available as "the strongest employer signal." **Consequence:** `docs/02`'s clustering method needs to lean more heavily on surname + donation-burst-timing signals, with postal code as a coarser supporting signal rather than a precise one. Log this before writing `docs/02`.

## 2026-08-02 — By-elections require separate contribution exports
The 2022–2026 council term had four by-elections: Mayor (Jun 2023), Ward 20 (Nov 2023), Ward 15 (Nov 2024), Ward 25 (Sep 2025) — confirmed complete against Toronto's official by-election results page and Wikipedia's Toronto City Council 2022–2026 page. Contributions for by-election winners live in election-scoped exports separate from the 2022 general file. All five files (2022 general + 4 by-elections) pulled via the blank-name/Export method and saved to `data/raw/efd_contributions/`. **Consequence for Phase 1/2:** the pipeline needs a per-councillor mapping of "which election put them in office" to know which contribution file to pull their donors from — this can't be assumed to be the 2022 general file for everyone.

## 2026-08-02 — Vote record has a 4th value not documented in the readme
The readme (`docs/00-getting-started.md` Step 2) says votes are recorded as "Yes", "No", or "Absent". The live data also has **`Absent(Interest Declared)`** (115 of 45,665 rows) — a member recording an explicit declared conflict of interest rather than a plain absence. This is directly relevant to the project's thesis (a councillor recusing from a development vote due to declared interest is a strong, self-reported signal) and should be treated as its own category in `docs/03`'s vote coding, not collapsed into "Absent."

## 2026-08-02 — 14 development applications have no ward assigned
Out of 26,368 rows, 14 (0.05%) have a null `WARD_NUMBER`/`WARD_NAME` — all old, `Closed`-status applications (application numbers ranging 2008–2021). Negligible for analysis; not investigated further.

## 2026-08-02 — RETRACTED: "mangled characters" finding was a false alarm
Originally logged as a data quality issue in `2023_mayor_byelection.xls` (names like "Bail[garbled]o, Ana"). On inspection with `[hex(ord(c)) for c in name]`, the character is `0xe3` — a correctly-encoded "ã". The name is genuinely "Bailão, Ana" (a real 2023 mayoral candidate). The garbling was my own terminal's display limitation (Windows console codepage) when I first printed the dataframe, not a problem in the source file or in `pandas`/`xlrd`'s reading of it. No cleanup needed. Lesson: verify apparent encoding issues at the code-point level before logging them as data problems — terminal rendering is not the same as the underlying string.
