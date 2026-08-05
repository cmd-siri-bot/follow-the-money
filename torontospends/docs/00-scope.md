# TorontoSpends — Scope & Delivery Plan (v2.1)
**Status:** Supersedes the v0.1 standalone scoping document. Built inside the same repository as Follow the Money, reusing its existing pipeline work. ADR-007 (repo/stack split) and hosting are now confirmed — see §1.
**Target dates:** Stage 1 live Oct 1, 2026 · Stage 2 (reduced scope) live Oct 20, 2026 · Stage 2 continuation and Stage 3 open-ended, after Oct 20
**Owner:** Siri
**Repo:** `https://github.com/cmd-siri-bot/follow-the-money`, working directory `C:\Users\iamsi\toronto-2026-election`. TorontoSpends lives at `torontospends/` within this repo — see §1.

---

## 0. What changed from v0.1

| v0.1 (Aug 5 draft) | v2 (this document) |
|---|---|
| Separate repo, Django scaffold from scratch | Same repo as Follow the Money; shares its data layer and entity-resolution code |
| Contract/grant history: "10 years ambitious, 5 years recommended" | **November 2022 → present**, matching the current council term — an editorial choice, not a time-box compromise (§6.1) |
| Open-ended calendar, phased by momentum | Two hard dates: Stage 1 by Oct 1, Stage 2 (reduced) by Oct 20 |
| Week-by-week schedule | Scope only — workstream-level hour estimates, no calendar breakdown (by request) |
| Entity resolution (§5.4, budgeted 20–25 hrs) scoped as new work | Substantially built already — this is adaptation, not construction |

Everything not listed above — product thesis, non-goals, legal/licensing posture, kill criteria — carries forward from v0.1 unchanged. Condensed versions are in §2, §9, §10 for reference; the full reasoning is still in the original document.

---

## 1. Repo & stack — ADR-007 (confirmed 2026-08-05)

**Decision:** TorontoSpends lives in the same git repository as Follow the Money. It does **not** inherit Follow the Money's stack (Python batch pipeline → static Astro site). It keeps its own serving layer — Django + Postgres + HTMX, per v0.1's ADR-001 — because the reasoning behind that choice is specific to TorontoSpends' review workflow and needs, and doesn't change just because the code lives in a shared repo:

1. **Human review workflow.** Statistical flags and AI-extracted entity merges need sign-off before going live. Django admin gives this almost for free (filter unreviewed, bulk-approve, audit trail).
2. **Search and querying.** TorontoSpends' product is fundamentally a database-backed app — users filter/search across budget lines, contracts, grants, and entities. Follow the Money's Astro static site publishes pre-computed findings; it has no live query layer to reuse. Django + Postgres gives this natively.

**What's actually shared:** a `common/` library — CKAN client patterns, name/entity normalization, PDF crawl→fetch→cache→extract infrastructure — that both projects' pipelines import from. Each project keeps its own extract/transform/analyze/publish layer and its own frontend.

**Hosting (confirmed 2026-08-05):**
- **Database:** Supabase free tier (Postgres). 500MB storage / 500MB RAM is comfortably sufficient for one council term of budget/contract/grant/lobbying data. **Known risk:** free projects auto-pause after 7 days with zero API requests — mitigate with a scheduled keep-warm health-check hitting the API (needs to actually be set up, e.g. a cheap cron ping, not assumed away).
- **App server:** Render free tier for Stage 1 (persistent, no credit card, but spins down after 15 min idle with 30+ second cold starts on wake). **Plan to move to a paid always-on tier before the Oct 20–26 window** — cold starts on a voter's first click, right before the election, are the wrong failure mode to accept for the sake of a free tier. Re-budget under §8.
- Domain: already owned, no incremental cost.

**Proposed repo layout:**

```
repo-root/
├── follow-the-money/        # existing — unchanged
│   ├── pipeline/
│   ├── docs/
│   └── site/
├── torontospends/            # new
│   ├── manage.py
│   ├── torontospends/        # Django project
│   ├── apps/                 # budget, lobbying, entities, annotation
│   └── docs/
└── common/                   # new — factored out of follow-the-money/pipeline
    ├── ckan_client.py
    ├── normalize_names.py
    ├── extract_role_name.py
    └── pdf_extraction/        # crawl/fetch/cache/extract/adjudicate pattern
```

Not yet built as of this writing — `torontospends/docs/` is the only part of this layout that exists on disk so far.

---

## 2. Product thesis & non-goals (carried forward from v0.1 §1)

Public, non-editorial, fully source-linked site making Toronto spending, contracting, and lobbying data searchable in plain language. Every displayed figure carries a source link and retrieval timestamp; statistical flags are described as statistical, never as findings; public corrections log. Not a news site, not FOI tooling, not real-time, money-and-influence only — no ridership, tree canopy, or 311 scope creep. Toronto-only through Stage 2; multi-municipality is Stage 3.

---

## 3. Reuse map — what Follow the Money already provides

| TorontoSpends need | Follow the Money asset (per Session 4 handoff) | State |
|---|---|---|
| Entity/org normalization & merging (v0.1 §5.4, budgeted 20–25 hrs) | `normalize_names.py` (incl. `normalize_postal()`), `build_knowledge_graph.py`'s `org_key()` merge logic | Built and tested — one real bug already found and fixed (postal-space formatting) |
| PDF crawl → fetch → cache → structured extraction → confidence gate → human review (v0.1 §5.2, Workstream A2 — "the long pole") | Same pipeline shape, already built for staff-report Application Data Sheets: 81 applicant/agent/architect/owner identities extracted this way | Built and working for a structurally similar document type — the single biggest reuse opportunity here |
| Free-text role/name extraction | `extract_role_name.py` — strips mailing addresses, classifies org- vs. person-shaped names | Built |
| Council voting record CKAN ingestion (v0.1 §6.5, Stage 3) | Source A already live and verified (`55ead013-...`), full 2022–2026 pull established | Built — not needed until Stage 3, but a zero-cost head start when it is |
| Lobbyist registry ingestion | Already core to Follow the Money's knowledge graph | Data already ingested; schema differs — Follow the Money models it as graph edges, TorontoSpends needs relational `fact_lobbying_registration` / `fact_lobbying_communication` rows. Ingestion risk reduced; adapter still needs writing |
| Human-review-queue pattern (sign-off before a named entity's data goes live) | `kg_adjudicate_applicant_overlaps.py`, `kg_adjudicate_owner_org_overlaps.py` | Pattern proven; Django admin is still the better interface at TorontoSpends' volume, but the review logic transfers directly |

**Not reusable — build fresh:** operating budget adapter, capital budget adapter, grant program adapters, the contracts data model itself, statistical flagging, dashboards, everything Django/Postgres-specific.

---

## 4. Data model

Canonical schema from v0.1 §3.1 carries forward unchanged: `raw_record` → `fact_*` → `annotation`, money as `amount_cents BIGINT`, every fact row traces to `source_url` + `retrieved_at`. No changes needed for the repo merge, the term-boundary decision, or the ADR-007 confirmation — the schema was already general enough.

---

## 5. Stage 1 — live by Oct 1

Scope unchanged from v0.1 §4: operating budget + lobbying registry, search, entity pages, freshness pipeline, `/status` + `/methodology` + `/corrections`. ~60 hr estimate holds. Eight weeks at the stated cadence is close to the original 5–7 week estimate — workable as written, no scope changes needed here.

**One addition from the reuse map:** deterministic entity normalization (v0.1's Week 3) is now an import, not a build. Small saving inside Stage 1, not load-bearing to the date.

---

## 6. Stage 2 — live by Oct 20 (reduced scope)

### 6.1 The term-boundary decision

**Decision:** contract and grant history covers **November 2022 (start of the current council term) to present**, not v0.1's default 5–10 year ambition.

**Reasoning:** this is a voter-facing civic transparency site shipping during an active municipal election. The current term is what a voter evaluating this council needs to see. History before the term is real analytical value, but it answers a different question — "how has Toronto spent over a decade" rather than "how has this council spent" — and that question doesn't need to be answered by Oct 20. State this boundary explicitly on `/methodology`, the same way Follow the Money states its own scope limits, so it reads as a deliberate editorial choice rather than a shortcut.

**Consequence for Workstream A2 (TMMIS backfill) — sizing spike run 2026-08-05:** v0.1's Appendix A (the document defining this spike's method) isn't in this repo, so the spike was run directly against the underlying question instead: how much of the Nov 2022–present award population needs PDF extraction versus already existing as structured data. Answer: **almost none of it does**. The Bids Portal's award data is published as an open CKAN dataset (`tobids-awarded-contracts`), and despite its own page claiming 18-month availability, the live datastore actually holds records back to 2010. Filtered to the term boundary: **1,096 structured records** fall in the 2022-11-15→2025-10-01 window A2 was assumed to need PDFs for. See `08-decision-log.md`'s 2026-08-05 TMMIS entry for the full check. A2 is no longer a PDF-extraction adaptation — see the revised line in §6.2.

### 6.2 Revised workstream scope for Oct 20

| Workstream | v0.1 estimate | Revised for Oct 20 | Why |
|---|---|---|---|
| A1 — rolling-window contracts | ~5–8 hrs | ~5–8 hrs | Unchanged, cheap, ship first regardless |
| A2 — TMMIS backfill | ~35–40 hrs (proportional share of 120) | **~5–8 hrs** | Sizing spike (2026-08-05) found the entire 2022–2025 award population — competitive (1,096 records) *and* non-competitive/>$30M (408 records, `tobids-non-competitive-contracts`) — is already structured CKAN data, no PDF extraction needed. Likely mergeable into A1 as a two-dataset date-filtered pull. Only unresolved sliver: neither dataset tags contract term, so >5yr-term contracts aren't separately filterable without a light text-parse of the competitive dataset's free-text description field — small, non-blocking |
| B — grant adapters | ~18–30 hrs (6–10 streams) | **~8–12 hrs** | Confirmed 2026-08-05: all City grant programs (105 distinct codes) live in one CKAN dataset (`community-grants-allocations`), not separate systems — one ingestion, not per-program adapters. Full Oct 20 editorial treatment (entity resolution, flag review, dashboard placement) goes to the top 4 by dollar volume: **TAC ($107.3M), CSP ($78.0M), SNP ($56.2M), YVP ($13.0M)** since 2022. Remaining ~100 codes ingested but not individually featured until Stage 2 continuation |
| C — entity resolution | ~20–25 hrs | **~5–10 hrs** | Adapting existing code, not building from zero |
| D — statistical flagging | included in Stage 2 total | **~8–12 hrs, reduced fidelity** | Computable on A1+B data only; TMMIS-dependent flags wait for fuller backfill |
| E — dashboards | included | **~5–10 hrs, partial** | Term-shading table (cheap, high-signal per v0.1) ships; full StatCan cost-of-living layer can trail |
| F — feeds & downloads | included | **~5 hrs, bulk download only** | RSS deferred; CSV/Parquet export is cheap and is the credibility-building piece — keep it |
| French (i18n) | ~12 hrs | **0 — deferred** | Already flagged as deferrable in v0.1 itself |

**Revised Stage 2 total for Oct 20: roughly 45–65 hrs**, down from v0.1's ~120 and from this document's own original 60–70 hr estimate — the A2 sizing spike (2026-08-05) shaved another ~5–12 hrs off once the PDF-extraction assumption was checked and dropped.

### 6.3 What's explicitly not done by Oct 20

Full 5-year TMMIS depth, remaining grant streams, the full statistical-flagging suite, the full dashboard/StatCan layer, RSS feeds, bilingual support. This becomes **"Stage 2, continued"** — rolling, no fixed date, the same relationship Stage 3 already has to Stage 2 in v0.1. Worth naming this explicitly (e.g. "Stage 2a / Stage 2b") so nothing gets silently counted as "done" that isn't, per v0.1 §5.9's own Definition of Done for full Stage 2.

---

## 7. Stage 3 — unchanged, open-ended, after Oct 20

No changes to v0.1 §6: lobbying↔procurement correlation, alerts/monetization, public API, development applications, council voting, multi-municipality expansion, semantic search — all as scoped, all gated behind the Stage 2 continuation and (§6.1 specifically) legal review before launch.

**Worth noting for later, not acting on now:** v0.1 §6.4–6.6 (development applications, council voting) overlap heavily with what Follow the Money has already built. When Stage 3 actually starts, that work is largely a port.

---

## 8. Cost — revised

| Line item | Stage 1 (by Oct 1) | Stage 2 (by Oct 20) | Notes |
|---|---|---|---|
| Hours | ~60 | ~60–70 | Combined ~120–130 hrs over 76 days ≈ **~11–12 hrs/week average** — close to v0.1's original 10–12 hr/wk baseline, not a late-stage sprint |
| Hosting — DB | $0 (Supabase free tier) | $0, or $25/mo if the 500MB/7-day-pause limits are hit before Oct 20 | Free tier confirmed sufficient for expected data volume; keep-warm ping still needs to be built (§1) |
| Hosting — app server | $0 (Render free tier, cold starts accepted pre-launch) | **Move to a paid always-on tier before Oct 20–26** (~$7–25/mo depending on plan) | Cold starts are an acceptable pre-launch tradeoff, not an acceptable one during the live election window |
| Claude API (annotation) | <$1 | ~$15–20 | Lower than v0.1's ~$30 — smaller PDF population to extract |
| Claude Code | $40–60 | $100–150 | Compressed window likely still needs Max 5x for part of Stage 2; re-check with `/usage` after the first two weeks |

---

## 9. Legal, licensing, ethics (carried forward from v0.1 §9)

Applies without modification: OGL-Toronto attribution sitewide, MFIPPA discipline on the lobbyist registry (republish, don't extend), neutral/quantitative language on every statistical flag, human review gate before anything affecting a named entity goes live, visible correction process, legal review specifically required before §6.1's Stage 3 lobbying↔procurement view ships.

**One addition specific to the merged repo:** Follow the Money's `docs/07-editorial-legal.md` was recently edited to remove two donor-privacy safeguards ("prefer cluster-level presentation," "no reverse lookup by donor name"). That's a Follow the Money-specific decision about named private campaign donors and shouldn't be assumed to carry over to TorontoSpends, where the equivalent population is contract vendors and lobbying clients, not individual citizens. Keep these two projects' privacy postures explicitly separate in whatever shared `docs/` structure ends up housing both.

---

## 10. Kill criteria (carried forward from v0.1 §8)

Stage 1 alone is a fully successful outcome if traction doesn't materialize post-launch. TMMIS scope caps further if the sizing spike comes back larger than expected. Alerts and other Stage 3 features get built on actual demand signal, not speculatively.

---

## 11. Open questions

1. ~~**ADR-007 (§1) needs confirming**~~ — **Resolved 2026-08-05.** Same repo, separate stacks, shared `common/` library, confirmed. Hosting confirmed as Supabase (DB) + Render (app server, free tier pre-launch → paid before Oct 20–26).
2. ~~**Where this document lives**~~ — **Resolved.** `torontospends/docs/00-scope.md`, mirroring Follow the Money's own `docs/` convention.
3. ~~**The TMMIS sizing spike**~~ — **Run 2026-08-05.** The Nov 2022–Oct 2025 award window turned out to already be structured data (1,096 records), not a PDF population — A2 revised down to ~5–8 hrs in §6.2. Full detail in `08-decision-log.md`.
4. ~~**The non-competitive / >$30M / >5yr-term award gap**~~ — **Investigated 2026-08-05.** Non-competitive and >$30M awards are both already structured CKAN data (`tobids-non-competitive-contracts`, 408 records in-window; confirmed up to $57M+ on record). Only the >5yr-term slice remains untagged in either dataset — a small, non-blocking gap, not a missing-data problem. Full detail in `08-decision-log.md`.
5. ~~**Which 3–4 grant programs** make the Oct 20 cut~~ — **Confirmed 2026-08-05.** By dollar volume since 2022: **Toronto Arts Council ($107.3M), Community Services Partnerships ($78.0M), Student Nutrition Program ($56.2M), Youth Violence Prevention Grants ($13.0M)**. Correction to this document's own earlier draft: CSP is not the largest single stream — TAC is, by a wide margin. Also found all ~105 grant programs share one CKAN dataset, so ingestion cost no longer scales with how many programs are "in scope" — see revised Workstream B in §6.2. Full detail in `08-decision-log.md`.

---

## 12. Decision log entries

See `torontospends/docs/08-decision-log.md`.
