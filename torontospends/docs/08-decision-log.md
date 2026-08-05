# TorontoSpends — Decision Log

## 2026-08-05 · TorontoSpends folded into the same repo as Follow the Money

**Decision:** TorontoSpends is built in the shared repo, reusing Follow the
Money's entity-normalization and PDF-extraction pipeline code via a shared
`common/` library. Each project keeps its own serving layer (TorontoSpends:
Django/Postgres; Follow the Money: Python batch + static site).

**Reason:** Significant real overlap in entity resolution and PDF-extraction
infrastructure; near-zero overlap in core datasets (budget/contracts/grants
vs. campaign contributions). Sharing the reusable layer without merging the
stacks avoids rebuilding proven code while keeping each project's own
architecture rationale intact.

**Consequence:** Stage 2 hour estimate for the Oct 20 slice drops from ~120
to ~60–70 hrs. `common/` needs factoring out of Follow the Money's
`pipeline/` before TorontoSpends' Stage 2 workstreams can import from it.

---

## 2026-08-05 · TorontoSpends contract/grant history bounded to the current council term

**Decision:** Contract and grant history covers November 2022 to present,
not a 5–10 year ambition.

**Reason:** Site is shipping during an active municipal election. The
current term is the relevant accountability window for a voter deciding
this election; pre-term history answers a different, still-valid question
that doesn't need answering by Oct 20.

**Consequence:** TMMIS backfill (Workstream A2) population shrinks from an
estimated 2,000–4,000 PDFs to roughly 400–1,000, pending the sizing spike.
Reopen after the election if historical depth becomes a priority again.

---

## 2026-08-05 · Stage 1 / Stage 2 target dates set

**Decision:** Stage 1 live by Oct 1, 2026. Stage 2 (reduced scope per
above) live by Oct 20, 2026. Stage 2's remaining v0.1 scope — full TMMIS
depth, full grant-stream coverage, full flagging/dashboard/feeds suite,
French — continues on a rolling basis after Oct 20 with no fixed date.

**Reason:** Election is Oct 26, 2026. Both dates chosen to give the site
real pre-election runway rather than landing in the final days.

**Consequence:** ~11–12 hrs/week average pace required through Oct 20,
close to original baseline cadence rather than a late sprint — contingent
on the ADR-007 and TMMIS-sizing open questions above resolving as expected.

---

## 2026-08-05 · ADR-007 confirmed: separate Django/Postgres stack, shared `common/` library

**Decision:** TorontoSpends keeps its own serving layer — Django + Postgres
+ HTMX — rather than adopting Follow the Money's Python-batch-pipeline +
static-Astro-site stack. Only the reusable data-processing layer
(`common/`: CKAN client, name/entity normalization, PDF crawl→fetch→cache→
extract) is shared between the two projects.

**Reason:** Two needs specific to TorontoSpends don't fit a static-site
pattern: (1) a human review workflow for statistical flags and AI-extracted
entity merges before they go live — Django admin provides this nearly for
free; (2) live search/filtering across budget, contract, grant, and entity
records — a database-backed query layer, not a set of pre-computed static
pages. Follow the Money's stack solves neither, so adopting it would mean
building both from scratch on the wrong foundation. The original ADR-001
reasoning (v0.1) holds regardless of which repo the code lives in.

**Consequence:** Two separate deployments/hosting setups to run and pay
for, not one. `common/` must be factored into an actually-importable
package (not just scripts in `follow-the-money/pipeline/`) before
TorontoSpends can depend on it — not yet done as of this entry.

---

## 2026-08-05 · Hosting: Supabase (DB) + Render (app server)

**Decision:** Postgres hosted on Supabase's free tier. Django app hosted on
Render, starting on its free tier for Stage 1 and moving to a paid
always-on tier before the Oct 20–26 window.

**Reason:** Both projects' domain costs are already sunk (owned domain).
Checked current (2026) free-tier terms rather than assuming stale pricing:
Supabase free gives 500MB Postgres storage/RAM, comfortably enough for one
council term of TorontoSpends data, but auto-pauses a project after 7 days
with zero API requests — a real risk for a site with uneven traffic, not
hypothetical. Render's free tier is the only genuinely persistent free
option for the app server among the ones checked (Railway and Fly.io no
longer offer real free tiers in 2026), but spins down after 15 minutes
idle with 30+ second cold starts on wake — an acceptable tradeoff before
launch, not during the live election window when a slow first load could
cost real credibility with a voter clicking in from social media.

**Consequence:** Two open follow-ups, neither done yet: (1) a scheduled
keep-warm health-check against the Supabase API to prevent the 7-day
pause; (2) a paid Render tier (or equivalent) needs to be budgeted and
switched on before Oct 20, not left on the free tier through the election
window. §8 of `00-scope.md` reflects both as re-budgeted line items.

**Reopen if:** Supabase's 500MB cap or the 50,000 MAU limit is actually hit
before Oct 20 (unlikely at TorontoSpends' expected scale, but unverified
against real data volume until Stage 1 build begins).

---

## 2026-08-05 · TMMIS sizing spike run — A2 does not need a PDF pipeline for its primary window

**Decision:** Workstream A2 ("TMMIS backfill") is rescoped from a PDF-
extraction problem to a structured-data ingestion problem, for the Nov
2022–Oct 2025 portion of its scope. See the revised A2 line in
`00-scope.md` §6.2.

**Reason:** v0.1's Appendix A (the document that was supposed to define
this spike's method) is not present anywhere in this repo and wasn't
available to run against — flagged rather than guessed at. Investigated
the underlying question directly instead: how much of the Nov 2022→present
contract-award population actually requires PDF scraping versus already
existing as structured data.

Checked live, not assumed:
- TMMIS itself: confirmed via `toronto.ca`'s own "Follow Up on City
  Contracts" page that as of Oct 1, 2025, competitive awards under $30M
  moved off TMMIS onto the new Toronto Bids Portal; TMMIS continues only
  for non-competitive procurements, awards over $30M, or contracts with
  terms over 5 years.
- The Bids Portal's award data is also published as an open CKAN dataset,
  `tobids-awarded-contracts` (resource id
  `e211f003-5909-4bea-bd96-d75899d8e612`), refreshed daily. Its own web
  page states awards are "available [on the portal] for 18 months after
  the date the contract is created" — but pulling the live datastore
  directly (7,608 total records) shows dates from 2010-04-15 through
  2026-07-29. **The 18-month claim describes the portal's browsable UI,
  not the open-data export** — a real discrepancy between the page's own
  stated limitation and what the API actually returns, not yet reconciled
  (see Reopen-if below).
- Filtered the live data to the term boundary: **1,096 records** fall
  between 2022-11-15 and 2025-10-01 (the actual candidate A2 backfill
  window), versus 6,131 before it and 293 after (already on the new
  portal going forward, A1's territory). All 1,096 are structured rows
  (supplier, dollar award, division, buyer, date) — no PDF needed for
  this window. The one caveat: post-Oct-2025 rows only carry an *initial*
  contract value in the "Award" field, needing the attached PDF for the
  true total — but that affects the 293 post-transition rows, not the
  1,096 in A2's actual scope.

**Consequence:** A2's 10–20 hr estimate (`00-scope.md` §6.2) is revised
down — it's now closer to A1's own ingestion shape (5–8 hrs) than a
PDF-extraction adaptation. The two workstreams may end up being the same
ingestion step with a date filter rather than separate builds.

**Not resolved by this spike:** whether non-competitive procurements,
awards over $30M, or >5yr-term contracts (the categories TMMIS keeps
handling even after Oct 1, 2025) show up anywhere in structured form, or
still require an actual PDF/TMMIS lookup. This is a real remaining gap in
A2's scope, smaller than originally assumed but not yet sized. Next task.

**Reopen if:** the "18 months" retention language turns out to apply to
the open dataset after all (e.g., a future check finds pre-2025 records
have disappeared from the live API) — would mean the current 1,096-record
snapshot needs to be archived promptly rather than assumed durably
available.

**Update, same day:** confirmed via the City's own staff report (`Ensuring
Continued Transparency in the Procurement Process`, June 27 2025,
2025.GG20 background file 256906) that "the Open Data Portal also
contains a record of contract awards posted in the Toronto Bids Portal,
**including those older than 18 months**, starting from February 2024" —
the 18-month figure is confirmed to describe the live portal's own
browse UI only, not the open-data export. This reopen condition is
resolved; no action needed unless a future check contradicts it.

---

## 2026-08-05 · Non-competitive and >$30M award gap also turns out to be structured, not PDF

**Decision:** the remaining TMMIS-retained categories (non-competitive
procurements, competitive awards over $30M) are folded into A2's revised
scope as structured-data ingestion, same as the base competitive-contract
window. Only "contract term exceeds 5 years" remains a genuine, smaller
gap — see below.

**Reason:** the same June 27 2025 staff report (2025.GG20 background file
256906) states plainly that "the Toronto Bids Portal... is a public
database of open competitive solicitations and awarded open competitive
**and non-competitive** contracts valued over $133,800," and that going
forward, non-competitive awards get posted the same way competitive ones
do. Checked live rather than trusting the report's framing alone:

- A separate, active CKAN dataset, `tobids-non-competitive-contracts`
  (resource `a11b18b4-72e6-47e3-a4e9-05dcc8abd697`), holds 2,925
  structured records, dated 2013-01-01 to 2026-12-18. **408 fall in the
  2022-11-15→2025-10-01 window.** Confirmed it includes large awards —
  the max on record is $57.2M (Veolia Water Canada, 2020), so the $30M
  threshold does not gate this dataset's coverage.
- Checked the competitive dataset (`tobids-awarded-contracts`) for the
  same threshold: 67 records ≥$30M. **One likely data-quality outlier
  flagged, not trusted at face value:** a $9.05 billion award to "Mr. Ron
  Weaver" (2017-05-17) — implausible for an individual recipient, almost
  certainly a source-data entry error. Not investigated further (out of
  scope for this spike), but anyone querying this field for a sum/max
  needs to know this row is in there.
- **Neither dataset has a contract-term/duration field.** The competitive
  dataset's free-text `Solicitation Document Description` sometimes
  states term length inline (e.g., "for a period of seventeen (17)
  months"), parseable with a regex/keyword pass rather than full PDF
  extraction — but this hasn't been attempted, and the non-competitive
  dataset has no equivalent description field at all to parse.

**Consequence:** of the three TMMIS-retained categories named in `00-
scope.md` §1, two (non-competitive, >$30M) are already fully covered by
structured open data — **1,504 total structured records** across both
datasets for the Nov 2022–Oct 2025 window (1,096 competitive + 408
non-competitive). Only the ">5 year term" slice remains genuinely
unresolved, and it's a filtering/tagging gap on records TorontoSpends
will already have, not a missing-data problem requiring new scraping.

**Not resolved by this spike:** how many of the already-captured award
records actually have a >5-year term, and whether a light text-pattern
pass on `Solicitation Document Description` recovers most of them or
whether this population needs to stay unflagged/undercounted. Small
enough in practice that it shouldn't block Stage 2 build start.

---

## 2026-08-05 · Grant program cut for Oct 20 confirmed — and the doc's own hunch was wrong

**Decision:** the four grant programs getting full Oct 20 treatment are
**Toronto Arts Council (TAC), Community Services Partnerships (CSP),
Student Nutrition Program (SNP), and Youth Violence Prevention Grants
(YVP)** — the four highest by total dollar volume since 2022.

**Reason:** v0.1's own list of "6–10 streams" isn't in this repo (same
gap as Appendix A), so checked live against the City's open data instead
of guessing. Found a single CKAN dataset, `community-grants-allocations`,
with a resource ("Community Grants Allocations since 2022," structured,
datastore-active, 6,511 records) covering **every** City community grant
program by recipient organization, funding program code, division, ward,
and dollar amount — not 6–10 separate systems needing separate adapters,
one unified source with a `Funding Program` field to group/filter by. A
companion resource ("Community Grants Programs since 2022") supplies the
acronym→full-name lookup.

Summed total funding by program across 2022–2025 (105 distinct program
codes appear in the live data):

| Program | Full name | Total $ (2022–2025) | Records |
|---|---|---|---|
| TAC | Toronto Arts Council | $107,273,470 | 1,993 |
| CSP | Community Services Partnerships | $77,968,092 | 697 |
| SNP | Student Nutrition Program | $56,248,800 | 10 |
| YVP | Youth Violence Prevention Grants | $12,993,207 | 58 |
| IMM | Immunization Action Plan | $10,768,500 | 68 |
| HPP | Homelessness Prevention Program | $9,585,234 | 54 |

**`00-scope.md`'s own draft assumption — "Community Service Partnerships
is likely the highest-value single stream" — turns out to be wrong.** TAC
is ~38% larger than CSP over the same window. Worth noting for the site's
own credibility: this is exactly the kind of assumption that needed
checking before publication, not just before scoping.

SNP's low record count (10) was checked before trusting it, not assumed
to be a data gap — the program funds two large intermediary foundations
(Angel Foundation for Learning, Toronto Foundation for Student Success)
who redistribute to individual schools themselves, so a genuinely large
program legitimately has few top-level grant rows.

**Consequence for Workstream B:** since all programs share one ingestion
source, the "6–10 streams" framing that drove the original per-program
adapter estimate doesn't really apply — there's one dataset to ingest,
not six to ten. The Oct 20 "cut" is better understood as which programs
get full editorial attention (entity-resolution cross-checking against
the lobbyist/donor knowledge graph, statistical-flag review, dashboard
placement) rather than which are technically feasible to pull in. TAC,
CSP, SNP, and YVP get that full treatment for Oct 20; the remaining ~100
program codes are still ingested (cheap, same source) but not
individually featured/reviewed until the Stage 2 continuation.

**Reopen if:** a future check of the full "Programs since 2022" lookup
table (159 codes, versus 105 actually appearing in the allocations data)
turns up a large program that's defined but not yet populated in the
live allocations resource — would mean this ranking is provisional on
data that hasn't caught up yet, not settled.

---

## 2026-08-05 · Stage 1 build started — common/, Django skeleton, first working adapter

**Decision:** built and verified, working tree only, nothing committed:

1. **`common/`** — `ckan_client.py` (generic paginated CKAN datastore
   fetch) and `normalize_names.py` (name/postal normalization + the new
   `org_key()`), both moved out of `pipeline/` rather than duplicated.
   `pipeline/fetch_ckan.py` and `pipeline/transform/normalize_names.py`
   now import from `common/` (the latter as a thin re-export shim so
   every existing script's `from normalize_names import ...` keeps
   working unchanged) and `pipeline/transform/build_knowledge_graph.py`
   imports `org_key` instead of defining its own copy. Verified
   byte-identical behavior against the pre-refactor functions before
   treating this as safe.
2. **Django project skeleton** at `torontospends/` — Django 6.0.8,
   settings read `DATABASE_URL` via `dj-database-url` (Supabase-ready,
   falls back to local sqlite when unset so the repo runs before a
   Supabase project exists), `django-htmx` and `whitenoise` wired in per
   the ADR-007/hosting decisions. `requirements.txt` and `.env.example`
   added. `TIME_ZONE = "America/Toronto"`.
3. **Four apps** (`apps/entities`, `apps/budget`, `apps/lobbying`,
   `apps/annotation`) with models mapped against real, already-verified
   data where it exists (lobbying: Follow the Money's actual
   `lobbyist_subject_matters.csv` / `_beneficiaries.csv` / `_firms.csv` /
   `_communications.csv` column names) rather than guessed. Budget's
   `FactBudgetLine` is flagged explicitly as a first pass, not yet
   checked against the live City operating-budget dataset's real schema
   — same "verify before building" gap as TMMIS/grants had, not yet
   closed.
4. **`Annotation`** model — generic (via `GenericForeignKey`) human-review
   queue, Django admin registered with bulk approve/reject actions that
   stamp reviewer + timestamp. This is the ADR-007 review-workflow
   requirement made concrete.
5. **First working data adapter**: `import_lobbying_registry`
   management command, reading Follow the Money's already-ingested
   interim CSVs (not re-fetching the registry ZIP from scratch) and
   loading them into the new relational schema. **Run against real data
   and verified, not just unit-tested:** 14,504 registrations, 140,921
   communications, 8,091 org entities, 12,975 person entities. Spot-
   checked sample rows (e.g. SM33270: Sean Meagher, Consultant, client
   Southdown Builders, firm ConveneToronto) by eye in the Django admin —
   correct.

**Not done yet:** the operating-budget adapter (needs the live-schema
check flagged above first), the search/entity-pages frontend, the
freshness pipeline, `/status`/`/methodology`/`/corrections`, and
deploying anywhere — this is local-only, sqlite-backed, unverified
against a real Supabase instance (no Supabase project exists yet; the
user needs to create that account/project themselves — not something
this assistant can do).

**Reopen if:** the operating-budget schema check turns up a materially
different shape than `FactBudgetLine` currently assumes — likely, given
it hasn't been checked yet, and should happen before that adapter is
built rather than after.

---

## 2026-08-05 · Supabase linked; operating-budget adapter built and verified against real data

**Decision:** `torontospends/.env` now points at the user's real Supabase
project (Session pooler mode, IPv4-compatible — chosen over Direct
connection, which is IPv6-only on the free tier and would likely fail
from Render). All migrations applied against real Postgres 17.6, not
just local sqlite.

**Safety note, fixed same session:** the user's actual Supabase DB
password was initially pasted into `.env.example` (a template meant to
be committed) rather than `.env` (gitignored). Moved to `.env`,
`.env.example` restored to a placeholder, confirmed `git check-ignore`
now correctly excludes `torontospends/.env`. Flagging this here so it's
not silently lost — check `git status`/`git diff` before any future
commit touches anything under `torontospends/` to confirm no credential
material is staged.

**Operating budget adapter:** built `import_operating_budget` management
command against the City's "Operating Budget Program Summary by
Expenditure Category" dataset (`common/ckan_client.py` gained a
`fetch_file`/`resource_download_url` helper for non-datastore
single-file resources, since this one — unlike the contract/grant data —
is published as one XLSX per fiscal year with no live query API).
Schema verified stable across FY2022-2025 before building
(`FactBudgetLine`'s field names were corrected to match the real
columns — `program`/`service`/`activity`/`category_name`/etc — replacing
the earlier guessed `division`/`vendor_entity` fields, which don't apply
to this dataset). Run against real data and loaded into the live
Supabase database: **78,978 budget lines across 4 fiscal years**
(19,714 / 20,127 / 18,585 / 20,552 for 2022-2025 respectively; 1,372
trailing blank rows in the 2024 file correctly skipped and spot-checked
harmless).

**Real finding, needs to reach `/methodology` before any dashboard uses
this data:** revenue lines are stored as **negative** dollar amounts in
the source data (a City accounting convention, not an ingestion bug) —
2025 shows $18.13B in Expenses rows and **-$19.27B** in Revenues rows.
Naively summing Expenses + Revenues does **not** yield Toronto's
reported net (tax-levy-funded) operating budget — the gross totals don't
net cleanly, almost certainly because of inter-program internal
recoveries/transfers counted as both an expense somewhere and a revenue
elsewhere. Computing an accurate net-budget figure needs real budget-
methodology rules, not a naive sum, and is explicitly **not attempted
here** — Stage 1 scope is ingest + search + entity pages, not a
computed headline number. Flagged now so whoever builds that later
doesn't get burned by it.

**Also confirmed:** the dataset's own last refresh was 2026-02-25 — six
months stale as of this session — and no FY2026 resource exists yet.
`RESOURCES` in the management command needs a new entry once the City
publishes it; this is exactly the kind of gap the Stage 1 "freshness
pipeline" workstream needs to detect and surface, not silently miss.

**Not investigated:** a separate dataset exists (`revenues-and-expenses`,
the Ontario Financial Information Return Schedules 10/40) with *actual*
year-end revenues/expenses, distinct from this *approved budget plan*
data. Not built against — Stage 1 scope says "operating budget," and the
approved-budget dataset matches that directly — but worth knowing this
exists if "actual vs. approved" ever becomes a wanted comparison.

---

## 2026-08-05 · Search + entity pages built; lobbying import rewritten for remote Postgres

**Decision:** built the first frontend (`base.html`, HTMX-powered live
search across budget/lobbying/entities, entity detail pages showing
lobbying registrations and communications by role). Also rewrote
`import_lobbying_registry` from row-by-row `get_or_create`/
`update_or_create` to batched entity resolution + `bulk_create` — the
original version worked fine against local sqlite but never completed
against real Supabase Postgres.

**Real problems hit and fixed, in order:**
1. The original per-row version left an **orphaned `idle in transaction`
   connection** on Supabase after being backgrounded and (presumed)
   abandoned — found via `pg_stat_activity`, killed with
   `pg_terminate_backend`. It was holding a lock that made every
   subsequent write attempt queue until Postgres's 2-minute
   `statement_timeout` fired. Worth knowing for future long-running
   commands against Supabase: check `pg_stat_activity` for stuck
   sessions before assuming a timeout means the new query is slow.
2. Even after that, a 1000-row `bulk_create` chunk on
   `FactLobbyingRegistration` (which has 3 FK columns + a unique
   constraint) was still too heavy per statement — reduced to a
   separate, smaller `WRITE_CHUNK` (200) for fact-table writes, kept
   entity resolution's reads/writes at the original 1000 (those stayed
   fast — plain lookups/inserts, no FK-heavy constraint checking).
3. **Real schema bug, not a performance issue:** `communication_method`
   was capped at `max_length=100`, but the real data isn't a short
   category — it includes free-text tails like `"Written;Other:Forwarded
   to Councillor Saxe, SickKids's Sustainability Strategy..."` up to 140
   chars. Checked the actual CSV column max lengths across all 5
   `POH_*`/`CommunicationMethod` fields before widening (only this one
   needed it) rather than guessing a bigger number.

**Consequence:** all real data now loads into Supabase successfully —
14,504 registrations, 140,921 communications, 21,066 entities, confirmed
by direct count and a spot-check search (`Bousfields Inc.`, previously
invisible because the data only existed in the old local sqlite db).

**Reopen if:** other fact-table imports (the future grant/contract
adapters) hit the same FK-heavy-bulk-insert slowness — the `WRITE_CHUNK`
pattern here is the fix, worth applying proactively rather than
rediscovering.

---

## 2026-08-05 · Browsable homepage built; /design-review skill declined

**Decision:** replaced the empty-search-box homepage with browsable entry
points -- the top 9 budget programs by FY2025 dollar volume and the top
9 most-lobbied-for organizations by registration count, as clickable
cards, plus a real (if modest) typography/color/spacing pass on
`base.html`. User's framing: people should be able to find their
favourite program without already knowing what to type.

**`/design-review` explicitly not used**, on request: that skill audits
and fixes an already-live page with one automatic git commit per fix,
which conflicts with this project's standing "commit only when
explicitly asked" rule, and there was no existing homepage to audit in
the first place -- this was a build, not a repair. Built directly
instead, no auto-commits, consistent with how the rest of this session
has worked.

**What the homepage cards actually link to:** budget program cards go to
`/?q=<program name>` (reusing the existing search view, since there's no
per-program detail page yet); lobbying-org cards go to the real entity
detail page. Both were click-tested end to end against live Supabase
data, not just eyeballed.

**Consequence:** the top-program and top-org queries are computed live
on every homepage request (two aggregate queries over ~79k and ~14.5k
rows respectively). Fine at current data volume; worth revisiting
(caching, or a precomputed summary table) if either table grows
substantially or the homepage becomes a real traffic target.

**Not done:** grant programs are deliberately absent from the homepage
-- no grant adapter exists yet (only budget + lobbying are ingested), so
featuring Toronto Arts Council/CSP/etc. as clickable homepage cards would
point at data that isn't there. Add once Workstream B is built.

---

## 2026-08-05 · Grant adapter built (Workstream B); grants now live everywhere the site touches data

**Decision:** built `apps/grants` (new app, not in the original proposed
`apps/{budget,lobbying,entities,annotation}` layout in §1 -- grants is
clearly its own domain, per the reuse map's own "not reusable -- build
fresh: ... grant program adapters" line) and `import_grants`, using the
CKAN resource ids already confirmed live during the earlier Oct-20
grant-cut decision (no re-investigation needed). Applied the
`WRITE_CHUNK`/batched-entity-resolution lesson from the lobbying rewrite
proactively this time, via a new shared `apps/entities/resolution.py`
(extracted from the lobbying command, which now imports from it instead
of carrying its own copy) -- no repeat of that debugging cycle.

**Two more real field-length bugs caught before they could fail
mid-run, same discipline as `communication_method` earlier:**
1. `Ward` isn't a single ward -- city-wide grant programs list many,
   comma-separated (243 chars observed). Widened from 200 to 1000 after
   checking the actual data, not guessing a bigger number.
2. `Funding Program` (what was assumed to always be a short code like
   "TAC") sometimes carries a full program name directly instead (up to
   60 chars observed, e.g. "Strategic Policy and Management Services
   Event Sponsorships") -- not every program has a separate acronym.
   Widened `funding_program_code` from 20 to 300.

**Result, run against real Supabase and verified:** 6,511 grant rows
loaded, 3,183 recipient organizations resolved as entities, 100%
recipient-resolution rate. Program totals matched the earlier live-data
check exactly (TAC $107.3M/1,993 grants, CSP $78.0M/697, SNP
$56.2M/10, YVP $13.0M/58) -- same numbers, now actually queryable in the
app instead of just a one-off research finding.

**Wired into every existing surface, not left as an orphaned table:**
search now covers grants (recipient name, program name/code, division),
entity detail pages gained a "Grants received" section, and the
homepage gained a third card row for the top 4 programs. Click-tested
end to end: searching "Toronto Arts Council" surfaces the TAC entity
itself, lobbying registrations *about* TAC funding (arts/culture
consultants lobbying on "Grants / Funding" subject matter -- a genuine
cross-reference the unified entity model was built for), and the actual
grant recipients under that program in one result set. A recipient
entity page (Against the Grain Theatre Inc.) correctly shows its full
grant history across all four ingested years.

**Consequence:** all three of Stage 1's core datasets (budget, lobbying,
grants) are now ingested, cross-referenced through one Entity table, and
reachable from the homepage without knowing what to search for.

---

## 2026-08-05 · Supabase keep-warm ping built; quick design pass ahead of a same-day demo

**Decision:** with a 6pm demo deadline and `/methodology`, `/status`,
`/corrections`, and the freshness pipeline explicitly deferred to
post-launch (user's call), spent the remaining time on the Supabase ping
and a fast usability pass instead.

**Supabase ping:** `ping_supabase` management command (trivial `SELECT
1`), tested working against the real project. Confirmed live (not
assumed) that direct DB queries count toward Supabase's activity clock,
not just REST API calls. `.github/workflows/supabase-keepalive.yml`
written, runs every 3 days -- but it's dormant: nothing in
`torontospends/` is pushed to GitHub yet, and the workflow needs
`DATABASE_URL` added as a repo secret once it is. Both are follow-ups
only the user can do.

**Design pass, done directly rather than via the `/design-review` skill**
(same reasoning as the homepage build: that skill's auto-commit-per-fix
workflow conflicts with "commit only when asked," and the git tree has
been dirty all session). Real, verified issue found and fixed: every
results table (9 across search + entity pages, up to 7 columns) had no
overflow handling -- on a real 375px mobile viewport this would have
broken page layout, not just looked cramped. Wrapped every table in a
`.table-wrap` (`overflow-x: auto`) and verified directly: at 375px, page
body no longer overflows, the table scrolls in its own container
instead. Also added a "browse instead" link to the no-results empty
state, since a dead end with no next action is exactly what the UX
principles this project already leans on (users don't read instructions,
give them somewhere to go) warn against.

**Not done:** a full audit against the rest of the design-review
checklist (typography scale, AI-slop patterns, full WCAG contrast
pass, etc.) -- scoped to what was fixable and verifiable in the time
available before 6pm, not exhaustive.

---

## 2026-08-05 · Real visual design pass + year-over-year budget "movers"

**Decision:** user reprioritized remaining pre-demo time toward making
the site actually look considered, plus a specific ask for homepage
"interesting bits" (programs that grew/shrank since 2022, not just
static totals).

**Visual design:** real typefaces via Google Fonts (Fraunces for
headings -- warm, editorial, distinctive; Inter for body -- consistent
cross-platform legibility) replacing the earlier Georgia-fallback
approach, confirmed loaded via `document.fonts.check()` rather than
assumed. Added a restrained per-domain color system (budget/lobbying/
grants each get a small text-tag color, not backgrounds or borders
everywhere -- avoids the generic-SaaS-card-grid look) and shadow-based
card hover elevation instead of the earlier flat border-color change.
Hero section gained a 3-stat row ($18.1B tracked, $419.2M in grants
since 2022, 14,504 lobbying registrations) -- ties visual polish
directly to real data rather than being decoration.

**Year-over-year budget movers, the actual "interesting bits" ask:**
compares approved-budget totals for each program between 2022 and 2025.
**Deliberately restricted to the 36 programs that (a) exist under the
exact same name in both years and (b) had at least $5M in 2022** --
checked live and confirmed some programs (e.g. "311 Toronto," found
earlier this session) were renamed/restructured between years, which
would otherwise show as a fake +/-100% swing that's really just an
accounting artifact, not a funding decision. The methodology caveat is
printed directly under the section heading, not hidden -- matches this
project's standing rule that a number without its limitation attached
isn't ready to publish.

**Real findings surfaced, both plausible against known public context
(not asserted as fact, just shown as data):** Children's Services +149%
since 2022 ($671.9M &rarr; $1.67B) -- consistent with Toronto's known
child-care expansion this term. Toronto Public Health -20% ($361.7M
&rarr; $288.6M) -- consistent with a post-pandemic funding drawdown.
Office of the CFO and Treasurer +255% is the largest mover by percentage
but smallest by dollar base ($16.6M &rarr; $58.8M) -- flagged internally
(not yet on the page) as a candidate for later methodology-page
discussion, since a 3.5x change on a small base is a different kind of
story than Children's Services' scale.

**Not done:** the same year-over-year treatment for grants (would need
the same renamed-program-style care given SNP's block-grant structure
found earlier) or lobbying. Scoped to budget only, given the time
available.
