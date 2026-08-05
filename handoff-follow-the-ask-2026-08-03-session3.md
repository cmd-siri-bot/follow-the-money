# Handoff: Follow the Ask (Toronto development-donor/vote analysis)
Generated 2026-08-03 · Session 3

## Objective
Data journalism piece + interactive site answering: do Toronto councillors who receive money from people in the development industry vote differently on development matters? Methodology has to survive hostile scrutiny. Target publication: mid-to-late September 2026 (Toronto municipal election Oct 26, 2026). Owner: Siri. Repo: `https://github.com/cmd-siri-bot/follow-the-money`, working directory `C:\Users\iamsi\toronto-2026-election`.

**Constraints (unchanged since Session 1):** every external data claim verified live, not assumed. Never put a number on the site that isn't computed from data in the repo. Every classification carries a confidence score, not a binary label. A null/inconclusive result published honestly is a stronger outcome than a strained correlation. Only commit to git when explicitly asked — held throughout this session too, with one exception: the user explicitly said "commit this" and later "push it" mid-session, both acted on immediately.

This session picked up both forked directions from the Session 2 handoff (lobbyist/donor deep-dive, motion-text scrape) and added a third: enhancing the lobbyist/donor knowledge graph with actual developer identities.

## Status

**Done, committed, and pushed to origin/main (commit `c851e28`):**
- **Lobbyist/donor knowledge graph** (`pipeline/transform/build_knowledge_graph.py`): entities for lobbyist registrants, firms, beneficiary corporate structure, donors, and members; edges for representation, corporate structure (typed by client/parent/subsidiary/controlling-interest), lobbying contacts, lobbying-to-a-specific-councillor's-office (structurally resolved via ward+date, with a real ward-numbering-reform trap caught and fixed), donations, and confidence-scored registrant↔donor identity links. 34,316 entities, 146,119 edges.
- **Manual adjudication of the 8 postal-code-corroborated lobbyist↔same-member-donor overlaps** (`audit/kg_lobbyist_donor_overlap_review.csv`) — all 8 hand-verified as clean matches (two heritage/OZ application refusals, one explicit height-increase amendment, others professional lobbyist-donor pairs). Two named people/firms worth remembering: **Joe Mihevc** (Mihevc Consulting and Mediation Ltd, ~25 dev-application filings) donated to both Matlow's and Perruzza's 2023 mayoral bids and has ongoing lobbying contact with both councillors' offices through 2026; **Peter Milczyn** (PM Strategies Inc, 40+ filings, the largest/most dev-concentrated book of the 8) gave $1,500 to Matlow's mayoral bid with 8 lobbying contacts 2023–2026.
- **Progress Toronto donor pull** (`pipeline/analyze/progress_toronto.py`) — turned out to already be sitting in the existing EFD contribution exports (`office == "Third Party Advertiser"`, excluded from `donors.csv` by `classify_donors.py`'s scope, not missing from the data). 132 contributions, 94 distinct donors, $35,075 net across 4 elections (2022 general, 2023 mayoral by-election, 2024 Ward 15, 2025 Ward 25). No lobbyist-registry name matches among its donors.
- **Motion-text scrape** (83 items with Amend-type motions, scraped via browser-session `fetch()` since `secure.toronto.ca` blocks bare HTTP) + **enriched Phase 3 rerun**: 4 of 141 Amend-type motions now resolve (was 0), vote inclusion grows 2.6%→2.8%. Two real false positives in the keyword classifier caught and fixed before trusting any output (see Decisions). **Verdict unchanged: still "cannot distinguish."** Positive-end odds ratio narrowed from ~6.9x to ~3.9x — real information gained, not enough to resolve the null result.

**Done, NOT yet committed (user has not been asked/hasn't said "commit this" for this piece):**
- **Development-application "who's the developer" extraction.** `development_applications.csv` has no applicant/owner field (confirmed in Session 2); the City's *live* Application Information Centre was checked fresh this session and also has no such field at the source-database level (see Dead ends). Pivoted to planning staff-report PDFs, which carry a standard "Application Data Sheet" attachment with real Applicant/Agent/Architect/Owner names.
  - `pipeline/transform/parse_application_data_sheet.py` — word-position (x0-coordinate) column reconstruction parser (these tables have no ruled grid lines, so `pdfplumber`'s table detector finds nothing, and plain text extraction interleaves columns).
  - `pipeline/transform/scrape_application_data_sheets.py` — full run across all 241 development items. Downloaded 659 PDFs (~1.5 GB, `data/raw/dev_application_pdfs/`, gitignored).
  - `pipeline/analyze/join_applicants.py` → `data/processed/development_applicants.csv`.
  - **Result: 81 of 241 items (33.6%) yielded a real Applicant/Owner name**; 69 with a machine-readable application number; 65 of those matched back to `development_applications.csv` by exact application-number join. Among items whose title looks like an actual application decision (222 of 241, filtering out policy reports/by-law amendments/area studies/Section 37 follow-ups), the rate is 36.0% (80/222) — lower than the 12-item feasibility sample (8/12) suggested; not fully explained. A real, known limitation: 40 of 241 items had more than 6 linked background PDFs and got truncated at a 6-PDF-per-item cap, so a Data Sheet living in a later document would be missed.
  - Real cross-validation win, unprompted: one sampled application's Owner field read "Samuel Sarick Limited / Graduate Holdings Limited" — the same family that independently showed up as lobbyist registrant Madeleine Sarick's business in the knowledge-graph adjudication.

**In progress:** nothing — this is a clean stopping point, mid-way through the graph-enhancement thread specifically (extraction is done, integration is not).

**Not started:**
- Feeding the 81 extracted applicant/agent/architect/owner names into the knowledge graph (name-matching against `donors.csv` and `dev_sector_reference.csv`, same confidence-scored approach as the registrant↔donor linking already built).
- Ontario Business Registry pull (director/officer data for beneficiary company names) — flagged repeatedly across sessions, never started.
- `docs/07`'s pre-publication checklist (right of reply, third-party advertiser registration check) — not started.
- Phase 4 (site build) — still blocked per `docs/06` until Phase 3 has a settled number; it still doesn't (enriched rerun didn't change the verdict).
- Committing/pushing this session's final piece (the development-applicant extraction) — waiting on explicit ask.

## Decisions

| Decision | Why | Reopen if |
|---|---|---|
| Lobbying-*contact-count* fields are not a meaningful metric | User correction: the Toronto lobbyist registry doesn't log every contact between a registrant and a public office holder, only what gets voluntarily filed. Treat `lobbied_office`/`lobbied_contact` edges as "contact happened at least once," never as a volume/intensity measure | If a different, actually-complete contact-logging data source is found |
| Lobbyist/donor knowledge graph built with full recall (Consultant-type registrants included, no dev-subject-matter filter), unlike Signal 3's precision-first donor classification | User's explicit framing: this is backend analytical infrastructure, not a public per-donor classification — the docs/07 "don't build a surveillance tool" question is a publication-layer decision, deferred to Phase 4 (already blocked), not something that has to be resolved to build the graph itself | If/when Phase 4 publication scope is decided |
| POH_Office → member resolution requires BOTH ward number AND ward-name text to match, gated by the member's actual term dates | Verified live: `lobbyist_communications.csv` spans 2000–2026 and pre-2018-reform rows use Toronto's old 44/47-ward numbering (e.g. "Ward 34 Don Valley East" = today's Ward 16). Number-only matching would have silently misattributed old contacts to whoever holds that number today | If communications data before 2018 needs its own historical ward-mapping table |
| Registrant↔donor identity links are confidence-scored (name-only vs. name+postal-corroborated), never asserted as fact | Same reasoning as Signal 3 — a shared name is not proof of a shared person. 823 total links, only 39 (4.7%) postal-corroborated; only the corroborated tier was treated as a real finding in the adjudication | Never, this is a permanent methodological stance |
| Enriched motion-direction classifier: bare `approve`/`restrict` keywords replaced with phrase-proximity requirements; 6-word window tightened to 3; hard length gate (1200 chars) added excluding omnibus amendments from keyword classification entirely | Two real false positives caught by reading the actual matched text before trusting the classifier: bare "approve" fired on "if approved" boilerplate unrelated to the amendment's own direction; a 6-word window matched "unit...increase" across an unrelated sentence in a 4,430-char omnibus Avenues policy amendment. Net effect: resolved count dropped from 21→4, all 4 hand-verified clean | If a human-reviewed pass (not a keyword classifier) is later applied to the excluded omnibus population |
| Application Information Centre / ArcGIS FeatureServer (`COTGEO_IBMS_AIC_POINT`) confirmed to have **no** applicant/owner/developer field, at the full 63-field schema level | Pulled the live FeatureServer's field list directly (`?f=json`) after the rendered page and direct URL navigation both failed/looped — this is the authoritative source-database schema, not just a display limitation. Only `ASSIGNEDPLANNER`/`ASSIGNEDPLANNER2` (City staff) fields exist | Never — this is a structural absence in the City's own data, not a scraping problem to solve later |
| `development_applications.csv`'s `application_url` column is stale | Confirmed live: it points to the retired `app.toronto.ca/AIC?folderRsn=...` pattern, which redirects to a modern page (`www.toronto.ca/.../application-details/?id=...&pid=...`) using different parameters entirely (`id`/`pid`, not `folderRsn`) | If `development_applications.csv` is ever re-pulled/refreshed from source |
| Application Data Sheet PDFs tried in ascending file-number order (earliest first), capped at 6 per item | Sample run showed the Data Sheet lives in the primary/original decision report, not later supplementary reports. Cap was a pragmatic bound given some items have 20-30+ linked background files; **known cost: 40 of 241 items had more than 6 files and got truncated, a real source of missed matches** | If coverage needs to improve — raising the cap or checking all linked files for capped items is the direct next step |

## Dead ends — don't retry

| Tried | What happened | Why it failed |
|---|---|---|
| Direct navigation to `app.toronto.ca/AIC/index.do?folderRsn=...` and its HTTPS/secure.toronto.ca equivalents | Consistent `navOk: false` / "denied or failed" across `navigate`, `preview_start`, and force-retry, even after a session pause and restart | Genuinely broken/retired path, not a transient issue — confirmed by finding the real modern URL pattern via the map widget's own JS data (`pageURL` field), which uses `?id=...&pid=...`, not `folderRsn=...` |
| Plain `curl`/fetch to `secure.toronto.ca/AIC/...` and `www.toronto.ca/.../application-details/` for real content | Both return either a 403-style block or a client-rendered "Loading" shell with no real data (confirmed via direct fetch — the actual content is a React/Next.js-style SPA, not server-rendered) | Same Akamai-style protection pattern as the rest of `secure.toronto.ca`; the `www.toronto.ca` application-details page specifically needs its JS to execute and populate from an in-memory dataset the previous search page loaded — cold/direct loads to that URL return an empty shell |
| `pdfplumber.extract_tables()` on Application Data Sheet pages | Returns 0 tables on every page checked | These tables use spacing/alignment, not ruled grid lines, so the line-based table detector has nothing to find. Word-position (x0) clustering against the header row's column starts was the working approach instead |
| Bare `\bapprove[ds]?\b` and 6-word-window keyword matching for the enriched motion-direction classifier | Produced 2 confirmed false positives (see Decisions) before being caught by manually reading the matched text | A proximity regex is not a substitute for reading a multi-page or even multi-sentence amendment; needed phrase-level requirements ("approve the application"/"the portion of the application") and a hard length gate, not just a tighter window |

## Corrections & preferences
Carried forward from Sessions 1–2 (still applicable):
- User is not deeply technical with devtools — give explicit step-by-step walkthroughs.
- Always sanity-check file content against filename claims.
- Only commit when explicitly asked; the user does ask directly and expects prompt action when they do ("commit this", "push it").
- User answers "Recommended" options quickly in `AskUserQuestion` prompts; trusts default judgment calls once the tradeoff is stated clearly.
- User proactively supplies context/corrections mid-task (e.g., "the number of lobbying contacts doesn't matter, they don't log contacts") — worth taking at face value and applying immediately, including retroactively to just-completed work if relevant.

New this session:
- **User dismissed one `AskUserQuestion` outright** ("Which entity/edge types for a first build pass?") rather than answering it — when that happened, the right move was to stop and wait for redirection, not push forward with a default choice. The user then said "let's keep going," which meant "make the call yourself and proceed," not "ask again." Distinguish between the user wanting to weigh in (answer questions promptly) and the user wanting momentum (dismissal + "keep going" = just proceed using your own judgment).
- User is comfortable with rapid direction changes mid-task (interrupting an active tool call with a new instruction, e.g. "lets pause this until my tokens reset" arriving mid-investigation, then "lets keep going" to resume) — pause cleanly and summarize state when interrupted, resume smoothly without re-litigating when told to continue.
- When the user gives a one-line follow-up request that assumes context ("scope the development application scraper," "pull a small sample first," "build the parser and run all 241"), they mean literally that scope, incrementally — not license to jump straight to the full end-to-end build. Each of those was a distinct, separately-approved step.
- For large scrapes, the user is fine with real resource use (659 PDFs, ~1.5 GB downloaded this session) once the task is clearly scoped and approved — no pushback received, but the download was still flagged explicitly before running at full scale, matching the "explicit permission for downloads" norm.

## Work products

| Item | What it is | Where it is | State |
|---|---|---|---|
| `docs/08-decision-log.md` | Full narrative log — read this first | committed | Extensively updated this session; current through the development-applicant extraction |
| `pipeline/transform/build_knowledge_graph.py` | Knowledge graph builder | committed | Working; outputs `data/interim/kg_entities.csv`, `kg_edges.csv` (gitignored, regenerable) |
| `pipeline/analyze/kg_summary.py`, `kg_adjudicate_overlaps.py` | Per-member cross-cut + manual adjudication of the 8 corroborated overlaps | committed | Working |
| `audit/kg_lobbyist_donor_overlap_review.csv` | Adjudication worksheet, `reviewer_verdict`/`reviewer_note` blank | committed | LLM first-pass done; needs the user's own read before any name goes further, same as `donor_review.csv` |
| `pipeline/analyze/progress_toronto.py` | Progress Toronto donor extraction | committed | Working; output `data/processed/progress_toronto_donors.csv` committed |
| `pipeline/transform/parse_motion_text.py`, `code_motion_direction_enriched.py` | Motion-text scrape parsing + enriched direction classification | committed | Working |
| `pipeline/analyze/specification_enriched.py`, `sensitivity_enriched.py`, `diagnostics_enriched.py` | Enriched Phase 3 rerun, mirrors the original three scripts exactly except vote source | committed | Working; outputs `phase3-*-result-enriched.md` and `data/processed/*_enriched.csv` all committed |
| `pipeline/transform/parse_application_data_sheet.py` | Column-aware Application Data Sheet PDF parser | **uncommitted** | Working, validated against the 12-item sample (8/8 clean extractions) |
| `pipeline/transform/scrape_application_data_sheets.py` | Full 241-item download + parse pipeline | **uncommitted** | Ran successfully; downloads to `data/raw/dev_application_pdfs/` (gitignored, ~1.5 GB, local only) |
| `pipeline/analyze/join_applicants.py` | Joins extracted applicants back to `development_applications.csv`, reports coverage | **uncommitted** | Working; output `data/processed/development_applicants.csv` **uncommitted** |
| `data/interim/application_data_sheets.csv` | Raw per-item extraction result (found/not-found, all four fields, matched PDF/page) | **local only, gitignored** | Present locally, regenerable by rerunning `scrape_application_data_sheets.py` (needs `data/raw/dev_application_bgrd_links/all_bgrd_links.json`, also gitignored/local-only) |
| `data/raw/dev_application_pdfs/*.pdf` | 659 downloaded staff-report PDFs | **local only, gitignored** | ~1.5 GB; not reproducible without rerunning the scrape (re-downloads are idempotent, script skips existing files) |
| `handoff-follow-the-ask-2026-08-03.md` | Session 2 handoff | committed | Superseded by this document for anything still-live; this one absorbs everything relevant |

**Important:** if a new chat runs against the same working directory, everything above — including gitignored `data/interim/`, `data/raw/` — will still be there locally. If a new chat runs somewhere else (fresh clone), only committed files travel; the gitignored files need their generating scripts rerun. The 659 PDFs specifically would need a full rerun of `scrape_application_data_sheets.py` (which re-fetches `data/raw/dev_application_bgrd_links/all_bgrd_links.json` — wait, that file itself is NOT regenerated by any committed script; **if this handoff is picked up in a fresh clone, the bgrd-link scrape (originally done via ad hoc browser JS batches, not a saved script) needs to be redone first** — this is a real gap, flagged honestly: the link-scraping step that fed `all_bgrd_links.json` was done interactively, not committed as a standalone reusable script.

## Verbatim
- Repo: `https://github.com/cmd-siri-bot/follow-the-money`, working dir `C:\Users\iamsi\toronto-2026-election`
- Latest pushed commit: `c851e28`
- Knowledge graph: 34,316 entities, 146,119 edges; 8 postal-code-corroborated lobbyist↔same-member-donor overlaps (out of 823 total name-matched links, 39 corroborated)
- Progress Toronto: 132 contributions, 94 donors, $35,075 net, 4 elections, 0 lobbyist-registry name matches
- Motion-text scrape enriched result (base threshold 0.5): coefficient **−2.5946** (p=0.2000), 95% CI **[−6.5625, 1.3733]**, n=1,239 included votes (vs. original −2.3310, p=0.2832, CI [−6.5881, 1.9262], n=1,154)
- Enriched sensitivity: strict −2.5322 (p=0.206) / base −2.5946 (p=0.200) / permissive −1.5606 (p=0.468), no direction flip
- Enriched leave-one-out: logistic coef range [−4.769, −1.946], 0/26 flip positive; Spearman rho range [−0.403, −0.233], 0/26 flip positive
- ArcGIS FeatureServer confirmed to have no applicant field: `https://services3.arcgis.com/b9WvedVPoizGfvfD/ArcGIS/rest/services/COTGEO_IBMS_AIC_POINT/FeatureServer/0` (63 fields, queried live via `?f=json`)
- Application Data Sheet extraction: 81 of 241 items found (33.6%); 36.0% (80/222) among items that look like actual application decisions; 65 matched back to `development_applications.csv`
- Two named cross-session-validated developer/lobbyist connections: Joe Mihevc (Mihevc Consulting and Mediation Ltd) and Peter Milczyn (PM Strategies Inc) — both donated to sitting councillors' mayoral bids and maintain active multi-year lobbying relationships with those same councillors' offices
- Samuel Sarick Limited / Graduate Holdings Limited — appeared independently as both a development-application Owner and a lobbyist registrant's (Madeleine Sarick's) business

## Open questions

**For the knowledge-graph enhancement thread (pick up here):**
- Feed the 81 extracted applicant/agent/architect/owner names into the knowledge graph as new entities, cross-linked to `donors.csv` and `dev_sector_reference.csv` by name, with the same postal-code-or-nothing confidence scoring already used for registrant↔donor links. This is the natural next step and wasn't started.
- Whether to raise the 6-PDF-per-item cap (or specifically re-check the 40 items that hit it) to improve the 33.6%/36.0% coverage rate — a real, bounded piece of unfinished work, not a redesign.
- Whether to also pull the Ontario Business Registry for the newly-extracted company names (Applicant/Owner entities) to resolve them to real directors/officers — same idea flagged for `dev_sector_reference.csv` in Session 2, now doubly relevant with this new company-name population.
- The `docs/07` "surveillance tool" framing question (publication-layer, not backend) is still explicitly deferred, per the user's own instruction this session to build the graph with full recall and worry about publication scope later.

**Still open from Session 2, untouched this session:**
- `docs/07`'s pre-publication checklist (right of reply, third-party advertiser registration check with the City Clerk).
- Phase 4 (site build) remains blocked — Phase 3's number is still "cannot distinguish" after the enriched rerun.

## Next action
Two candidate next steps, not mutually exclusive:
1. **Finish the graph-enhancement thread**: name-match the 81 extracted applicants/owners against `donors.csv` and `dev_sector_reference.csv`, same confidence-scoring pattern as the existing registrant↔donor links, and report what (if anything) turns up. This is the most direct continuation of "what other information would the graph need to be functional?"
2. **Commit this session's uncommitted work** (`parse_application_data_sheet.py`, `scrape_application_data_sheets.py`, `join_applicants.py`, `data/processed/development_applicants.csv`) — waiting on an explicit "commit this," per the standing rule.

If a new chat picks this up: read `docs/08-decision-log.md` first (as always), then check whether `data/interim/application_data_sheets.csv` and `data/raw/dev_application_pdfs/` are still present locally before deciding whether to re-run anything — they're gitignored but should persist in this working directory across sessions.
