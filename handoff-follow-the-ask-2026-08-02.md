# Handoff: Follow the Ask (Toronto development-donor/vote analysis)
Generated 2026-08-02 · Session 1

## Objective
A data journalism piece + interactive site answering: do Toronto councillors who receive money from people in the development industry vote differently on development matters? Portfolio piece — the methodology has to survive hostile scrutiny (a Toronto Star reporter or councillor's staffer reading the methodology page should find no hole in it), regardless of what the final number turns out to be. Target publication: mid-to-late September 2026 (Toronto municipal election is October 26, 2026). Owner: Siri. Repo: **https://github.com/cmd-siri-bot/follow-the-money** (pushed, `main` branch, 2 commits as of this handoff).

**Constraints:** every external data claim must be verified live, not assumed (this bit the project twice already — see Decisions). Never put a number on the site that isn't computed from data in the repo. Every classification needs a confidence score, not a binary label. If the data doesn't support the "donors → votes" thesis, say so — a null result published honestly is the stronger outcome, not a failure.

## Status
**Done:**
- Phase 0 (feasibility) — full go/no-go completed, verdict **GO, full scope** (all 26 wards + mayor).
- Phase 1 (extraction) — all raw datasets pulled and normalized into `data/interim/` (see Work products). Pipeline scripts committed.
- Repo scaffolded, git initialized, both phases committed and pushed to GitHub.

**In progress:** nothing actively mid-build.

**Not started:**
- Phase 2 — donor industry classification (clustering) + development-vote coding. **This is the critical path per the strategy doc**, more important than any frontend work.
- Phase 3 — pre-registered analysis, producing the actual number.
- Phase 4 — static site build. **Explicitly must not start before Phase 3 has a number** — the strategy doc is emphatic that the design should be built around the real finding, not a placeholder.
- `docs/02` through `docs/07` (donor classification method, vote coding definition, methodology/pre-registration, pipeline schemas, frontend spec, editorial/legal checklist) — **only `docs/00` and `docs/08` exist in this repo.** See Open questions — this is likely the single most important thing to resolve before Phase 2 starts.

## Decisions
| Decision | Why | Reopen if |
|---|---|---|
| Repo scaffolded directly in `C:\Users\iamsi\toronto-2026-election` rather than a nested `follow-the-ask/` subfolder | Directory was empty and already dedicated to this project | Never — cosmetic only |
| Vote record (`55ead013-2331-4686-9895-9e8145b94189`) verified live, 45,665 rows, `Agenda Item #` present as join key | Confirms the join key the whole votes↔dev-applications link depends on | — |
| Vote values include an undocumented 4th value: `Absent(Interest Declared)` (115 rows) | Not in the CKAN readme, but directly relevant to the thesis (self-reported conflict of interest on a vote) | When writing `docs/03` vote coding — treat as its own category, not folded into "Absent" |
| Lobbyist Registry has no datastore API — only a ZIP of two large XML files (`lobbyactivity-active.xml`, `lobbyactivity-closed.xml`) | `datastore_active: False` on the CKAN resource | — |
| EFD site (`app.toronto.ca/EFD`) cannot be scraped headlessly | `app.toronto.ca` refuses HTTPS outright; real host is `secure.toronto.ca` behind an Akamai WAF that 403s non-browser traffic | If building an automated re-scrape later, must go through a real browser session, not `requests`/headless tools |
| **EFD scraping problem eliminated**: blank candidate-name search + the page's "Export" button returns a bulk `.xls` of every matching row for an election, under the 55,000-row cap | Verified directly — one export got all 10,265 rows of the 2022 general election in one file | — |
| Contribution data has postal code only, not full street address | Site withholds full address under MFIPPA s.14 | `STRATEGY.md` section 3.1 assumed full addresses for employer clustering — `docs/02`'s method needs to lean more on surname + donation-burst-timing, less on address precision |
| By-elections require separate contribution exports from the 2022 general | Verified against Toronto's official by-election results page + Wikipedia: Mayor (Jun 2023), Ward 20 (Nov 2023), Ward 15 (Nov 2024), Ward 25 (Sep 2025) — confirmed complete, no others this term | Pipeline must map "which election put this sitting councillor in office" before pulling their donor list |
| `data/interim/` added to `.gitignore` alongside `data/raw/` | Matches strategy doc's stated convention that only `data/processed/` (final published artifacts) is committed | If the convention changes |

## Dead ends — don't retry
| Tried | What happened | Why it failed |
|---|---|---|
| Plain `requests.get('https://app.toronto.ca/...')` | `ConnectTimeout` | `app.toronto.ca` doesn't serve HTTPS on port 443 at all |
| `WebFetch` tool on `http://app.toronto.ca/...` | Silently upgraded to HTTPS, then `ECONNREFUSED` | Tool auto-upgrades `http://` → `https://`; can't be used to test the plain-HTTP path |
| Direct `requests` to `http://app.toronto.ca/...` (real plain HTTP, via Python, not WebFetch) | 302 to `https://secure.toronto.ca/...`, then `403 Access Denied` (Akamai edge) | WAF blocks datacenter-IP/bot-signature traffic; needs a real browser session |
| Browser automation tool (`mcp__Claude_Browser__*`) against `app.toronto.ca` | Navigation denied/timed out repeatedly | Confirmed unrelated to the target site — a neutral test navigation to `example.com` *also* timed out in the same session, indicating the tool itself was non-functional this session, not a site-specific block |
| Flagged "mangled characters" in `2023_mayor_byelection.xls` names as a data quality bug | Retracted | Checked the actual code point (`0xe3`) — it's a correctly-encoded "ã" ("Bailão, Ana"). The garbling was my own terminal's display limitation, not a real issue. Logged and corrected in `docs/08-decision-log.md`. |

## Corrections & preferences
- User is not deeply technical with devtools — when asked to check the Network tab, needed an explicit step-by-step walkthrough (F12, Preserve log, Fetch/XHR filter, etc.), not just "check devtools."
- The EFD site's contribution export only works via **manual browser interaction** (search + click Export) — the user did this themselves for all 5 election files. There is no working automated path in this environment. Future data pulls (if the site itself changes, or new elections/wards are needed) should assume the user does the manual export-and-share step, not an automated scraper.
- User caught a real error I would have missed: one of the files I was given (labeled "mayior 2023") was actually a duplicate of the Ward 20 by-election file, not the real mayoral by-election. Always sanity-check file content against filename claims (I now do this by reading the "Election:" metadata row embedded in each export before trusting the filename).
- Only commit to git when explicitly asked — this was followed correctly this session (asked before both commits).

## Work products
| Item | What it is | Where it is | State |
|---|---|---|---|
| `STRATEGY.md` | Full project strategy doc | repo root, committed | Complete, unchanged from original |
| `docs/00-getting-started.md` | Phase 0 checklist | committed | Complete, unchanged from original |
| `docs/08-decision-log.md` | Running decision log — **read this first in a new session** | committed | Complete through Phase 1, actively maintained |
| `phase0-findings.md` | Go/no-go write-up | repo root, committed | Complete, includes the retraction note |
| `handoff-follow-the-ask-2026-08-02.md` | This file | repo root, **not yet committed** | — |
| `pipeline/fetch_ckan.py` | Pulls full votes + dev-applications datasets from CKAN, paginated | committed | Working, re-runnable anytime (hits live API) |
| `pipeline/parse_contributions.py` | Normalizes the 5 EFD `.xls` exports into one table, tags election/year, parses dates | committed | Working |
| `pipeline/parse_votes.py` | Cleans vote record, handles the "24hr time + spurious AM/PM suffix" date quirk | committed | Working |
| `pipeline/parse_dev_applications.py` | Cleans dev applications, types dates/ward numbers | committed | Working |
| `pipeline/parse_lobbyist_registry.py` | Streaming XML parser (`iterparse`) flattening the 150MB+59MB lobbyist XML into 4 normalized CSVs | committed | Working |
| `data/raw/*` (votes, dev apps, city wards, lobbyist ZIP, 5 EFD `.xls` files) | Raw source data | **local only, gitignored, NOT in GitHub** | Present in the local working directory `C:\Users\iamsi\toronto-2026-election\data\raw\` |
| `data/interim/*` (votes.csv, contributions.csv, development_applications.csv, 4 lobbyist CSVs) | Cleaned/normalized tables | **local only, gitignored, NOT in GitHub** | Present locally; regenerable by re-running the pipeline scripts *except* the 5 EFD `.xls` files, which require the manual browser export step (see Corrections) |

**Important:** because `data/raw/` and `data/interim/` are gitignored, they exist only in the local filesystem at `C:\Users\iamsi\toronto-2026-election`. If a new chat session runs against that same directory, they'll still be there. If it runs anywhere else, they won't — the votes/dev-applications/city-wards/lobbyist-ZIP raw pulls can be regenerated by re-running `pipeline/fetch_ckan.py` and re-downloading the lobbyist ZIP, but the 5 EFD contribution `.xls` files cannot be regenerated by script — they require redoing the manual search+Export steps on `secure.toronto.ca/EFD`.

## Verbatim
- CKAN base: `https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action`
- Votes resource ID: `55ead013-2331-4686-9895-9e8145b94189` (45,665 rows)
- Votes readme resource ID: `6f7d8bb7-6ae4-4a15-8b01-b95a81c35dfe`
- Development applications resource ID: `8907d8ed-c515-4ce9-b674-9f8c6eefcf0d` (26,368 rows)
- City wards resource ID: `7672dac5-b383-4d7c-90ec-291dc69d37bf` (25 rows, GeoJSON geometry embedded)
- Lobbyist registry ZIP resource ID: `94c1fe59-7247-4b92-b213-950f71e04aff`, URL: `https://ckan0.cf.opendata.inter.prod-toronto.ca/dataset/6a87b8bf-f4df-4762-b5dc-bf393336687b/resource/94c1fe59-7247-4b92-b213-950f71e04aff/download/lobbyactivity.zip`
- EFD real host: `secure.toronto.ca` (not `app.toronto.ca`, which only redirects)
- EFD contribution search page: `/EFD/jsf/contribution/contribution_search.xhtml?campaign=9`
- GitHub repo: `https://github.com/cmd-siri-bot/follow-the-money`
- Contribution rows by election: 2022 general 10,265 · 2023 mayor by-election 11,858 · 2023 Ward 20 632 · 2024 Ward 15 562 · 2025 Ward 25 688 (total 24,005)
- Contribution rows by office (all elections combined): Mayor 14,595 · Councillor 8,326 · Toronto District School Board 805 · Toronto Catholic District School Board 133 · Third Party Advertiser 146
- By-election dates (verified via Wikipedia + toronto.ca): Mayor Jun 26 2023, Ward 20 Nov 30 2023, Ward 15 Nov 4 2024, Ward 25 Sep 29 2025
- Vote values found: `Yes` (32,364), `No` (8,834), `Absent` (4,352), `Absent(Interest Declared)` (115)

## Open questions
- **Do `docs/02-donor-classification.md`, `docs/03-vote-coding.md`, `docs/04-methodology.md`, `docs/05-pipeline.md`, `docs/06-frontend.md`, and `docs/07-editorial-legal.md` already exist as authored documents** (the way `STRATEGY.md` and `docs/00-getting-started.md` were provided as files at the start of this session), or do they need to be drafted from scratch as part of Phase 2/3/4? `STRATEGY.md` section 7 references them as if they exist and just haven't been shared yet. **This needs resolving before Phase 2 starts** — if the user has an authored classification method in `docs/02`, it should be followed; if not, the method has to be designed now, informed by the postal-code-only constraint discovered in Phase 0.
- Should Phase 2 begin next session, or does the user want to review the interim data first?

## Next action
Ask the user whether `docs/02` through `docs/07` already exist (and get them attached/pasted if so). If they don't exist yet, start Phase 2 by drafting the donor-classification method (`docs/02`), explicitly accounting for the postal-code-only address signal and the by-election donor-file mapping, before writing any classification code.
