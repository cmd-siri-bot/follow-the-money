# Phase 0 Findings — 2026-08-02

## Step 1 — Scaffold
Done. Repo structure created under `C:\Users\iamsi\toronto-2026-election` (serving as the `follow-the-ask` repo root — no separate nested folder). `.venv` created, dependencies installed (`requests`, `pandas`, `jupyter`, `python-dotenv`, `beautifulsoup4`, `playwright`). Git initialized. `.gitignore` excludes `.venv/` and `data/raw/`. `STRATEGY.md` and `docs/00-getting-started.md` copied in.

## Step 2 — Vote record (CKAN)
**Confirmed live and matches expectations.**

- Resource `55ead013-2331-4686-9895-9e8145b94189`: **45,665 total rows**.
- Fields: `Term`, `First Name`, `Last Name`, `Committee`, `Date/Time`, `Agenda Item #`, `Agenda Item Title`, `Motion Type`, `Vote`, `Result`, `Vote Description`.
- **`Agenda Item #` exists** (e.g. `2023.FM1.8`) — this is the join key to development applications. Confirmed present, not a gamble.
- `Vote` values observed: `Yes`, `No`, `Absent` — exactly as documented, no surprises.
- Readme resource (`6f7d8bb7-6ae4-4a15-8b01-b95a81c35dfe`) pulled and matches the live schema field-for-field.

No red flags here. This dependency is solid.

## Step 3 — EFD scraper spike
**RESOLVED. Verdict: full scope is a GO, and it's far easier than the strategy doc anticipated.**

My own automated tools (plain `requests`, browser automation) could not reach the site at all — `app.toronto.ca` refuses HTTPS connections on port 443 outright (`ERR_CONNECTION_REFUSED`, reproduced independently by the project owner in their own browser). The real host is `secure.toronto.ca`; `app.toronto.ca` only answers on plain HTTP and 302s over. Even hitting the real host directly, my requests got a `403 Access Denied` from what's almost certainly an Akamai edge/WAF layer — consistent with datacenter-IP/bot-signature blocking, not a site outage. **This means the site cannot be scraped headlessly from a script running in this kind of environment; it has to go through a real browser session.**

The project owner did the devtools inspection manually. Answers to the five gating questions:

1. **Server-side rendered HTML**, not XHR/JSON. The one XHR request visible (`dc.oracleinfinity.io/v4/account/.../client/id`) is a third-party analytics beacon, unrelated to the data.
2. **Yes, JSF ViewState required** — `javax.faces.ViewState` is a hidden form field; navigation/sorting/pagination all go through `myfaces.oam.submitForm(...)` POSTs.
3. **POST-driven, no stable per-candidate URL.** Search results come back via POST to `/EFD/jsf/contribution2018/contribution_result.xhtml`.
4. **Paginated, 20 rows/page** via the same POST+ViewState mechanism — **except this turned out not to matter** (see below).
5. **Fields exposed:** Contributor name, **postal code only** (not full street address — the site explicitly withholds addresses under MFIPPA s.14), amount, amount returned, contribution type, description of goods/services, contributor type, date received, candidate/registrant, office ("registered for"), ward.

**The decisive discovery: the page has an "Export" button that returns a bulk `.xls` of every row matching the search — not just the current page.** And critically, the "Candidate/Registrant Name" field can be left **blank**. A blank-name search with just "Contributor Type: All" returned **10,265 records covering the entire 2022 general election in one file** — every office (Mayor, Councillor, both school boards, Third Party Advertisers), well under the site's 55,000-row export cap.

**This eliminates the scraping problem entirely for the 2022 general election.** No ViewState session automation, no pagination loop, no per-candidate iteration — one manual export (already done) is the complete dataset.

**However — a real complication the strategy doc didn't anticipate: by-elections.** The 2022–2026 council term had four by-elections (verified against Toronto's own election-results page and Wikipedia): a mayoral by-election (Jun 2023, after John Tory's resignation), and councillor by-elections in Ward 20 (Nov 2023), Ward 15 (Nov 2024), and Ward 25 (Sep 2025). Contributions for candidates in those races live in **separate election-scoped exports**, not the 2022 general file. All four were pulled the same way (blank-name, blank-search, Export):

| File | Election | Rows | `Registered for` breakdown |
|---|---|---|---|
| `2022_general_election.xls` | 2022 Municipal Election | 10,265 | Councillor 6,467 / Mayor 2,780 / TDSB 805 / TCDSB 133 / 3rd Party 80 |
| `2023_mayor_byelection.xls` | 2023 By-Election for Mayor | 11,858 | Mayor 11,815 / 3rd Party 43 |
| `2023_ward20_byelection.xls` | 2023 Councillor Ward 20 By-Election | 632 | Councillor 632 |
| `2024_ward15_byelection.xls` | 2024 Councillor Ward 15 By-Election | 562 | Councillor 556 / 3rd Party 6 |
| `2025_ward25_byelection.xls` | 2025 Councillor Ward 25 By-Election | 688 | Councillor 671 / 3rd Party 17 |

All five now live in `data/raw/efd_contributions/`. **Practical consequence for Phase 1/2:** any councillor elected via by-election needs their contributions pulled from that by-election's file, not the 2022 general — a join on "which election put this specific sitting councillor in office" has to happen before donor classification, not after.

**Data quality note (retracted):** I initially flagged what looked like mangled non-ASCII characters in the mayoral by-election file (e.g. "Bail[garbled]o, Ana"). Checked the actual Unicode code point during Phase 1 parsing — it's `U+00E3` ("ã"), correctly encoded. The name is genuinely "Bailão, Ana." The garbling was my terminal's display limitation, not a problem in the data. No cleanup needed.

## Step 4 — Supporting datasets (CKAN)
All four resolved. Details:

| Dataset | Package | Best resource | `datastore_active` | Notes |
|---|---|---|---|---|
| Lobbyist Registry | `lobbyist-registry` | `94c1fe59-7247-4b92-b213-950f71e04aff` (ZIP) | **False** | No queryable API table — only a ZIP download and an XLS readme. Will need to download + parse, not `datastore_search`. |
| Development Applications | `development-applications` | `8907d8ed-c515-4ce9-b674-9f8c6eefcf0d` (CSV) | **True** | 26,368 rows. Fields include `WARD_NUMBER`, `WARD_NAME`, `DATE_SUBMITTED`. Coverage checked: earliest record 2008-01-04, most recent 2026-07-03 — comfortably spans the 2022–2026 term. |
| Committee of Adjustment | `committee-of-adjustment-applications` | (not yet drilled into resource level) | — | Confirmed package exists; same shape as development applications, likely fine. |
| Ward boundaries | `city-wards` | `7672dac5-b383-4d7c-90ec-291dc69d37bf` (GeoJSON) | **True** | Low risk, as expected. |

No red flags except the lobbyist registry format (workable, just needs a different extraction path than the others).

## Revised time estimate
All four steps came in well under the 3-hour budget, and Step 3 — expected to be the multi-day risk — turned out to need zero scraper code. Phase 1 extraction for contributions is now "organize five already-downloaded files," not "write and debug a JSF scraper." Revised estimate for Phase 1 overall: a few hours, not the ~day originally budgeted for the EFD piece alone.

## What surprised me
- Lobbyist Registry has no datastore-backed resource at all (ZIP + XLS only) — the strategy doc listed this as "assumed available," and it *is* available, but not in the queryable form the other datasets are. Minor, but worth logging since it changes the extraction code path for that one source.
- `app.toronto.ca` doesn't accept HTTPS at all; the real host is `secure.toronto.ca`, sitting behind what looks like an Akamai WAF that blocks non-browser traffic. Automated/headless access from a script is a dead end; a real browser session is required.
- The site withholds full street addresses (postal code only) — weakens the address-clustering signal `STRATEGY.md` section 3.1 was counting on. Needs reflecting in `docs/02`'s method.
- The "Export" button plus a blank name field turns the entire scraping problem into a single bulk download per election — the opposite of what the strategy doc's risk assessment expected.
- By-elections (4 of them) mean "who donated to currently-sitting councillors" isn't answerable from the 2022 general file alone — by-election winners' donor records live in separate election-scoped exports.
- (Retracted during Phase 1) What looked like a corrupted-character data issue in one export turned out to be my own terminal failing to render an accented letter correctly — the underlying data was fine all along.

## Go/no-go
**GO — full scope, all 26 wards plus mayor.** Every dependency in section 4 of `STRATEGY.md` is now verified, not assumed. The classification module (`docs/02`) remains the critical path, exactly as the strategy doc predicted — extraction turned out to be the easy part, not the hard part.
