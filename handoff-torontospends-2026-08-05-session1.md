# Handoff: TorontoSpends Stage 1 build — Session 1
Generated 2026-08-05 · Session 1 (TorontoSpends' first working session; Follow the Money's own handoffs are separate, most recent is `handoff-follow-the-ask-2026-08-05-session4.md`)

## Objective
TorontoSpends is a civic-transparency site (Toronto operating budget, contracts, grants, lobbying) built inside this same repo as Follow the Money, per ADR-007. Target: Stage 1 live Oct 1, 2026; Stage 2 (reduced scope) Oct 20, 2026; Toronto municipal election Oct 26, 2026. Owner: Siri. Repo: `https://github.com/cmd-siri-bot/follow-the-money`, working directory `C:\Users\iamsi\toronto-2026-election`, TorontoSpends' own code at `torontospends/`.

**This session's actual scope, in order:** finalize ADR-007 (Django/Postgres, separate from Follow the Money's Python-batch/static-site stack) and hosting (Supabase + Render) → run the TMMIS/grant-program sizing spikes that were the last open items in the scope doc → build Stage 1: Django project, three data adapters against real Supabase data, a working frontend (search, entity pages, browsable homepage) → a live-database keep-warm mechanism → design polish and a homepage "interesting facts" feature, prioritized ahead of a same-day 6pm demo, with `/methodology`, `/status`, `/corrections`, and the freshness pipeline explicitly deferred to post-launch on the user's instruction → commit and push.

## Status

**Committed and pushed to `origin/developer-identity-extraction`** (this branch is not yet merged to `main`; confirm with `git log main..HEAD` before assuming otherwise):
- `dc9e1fd` — "Add TorontoSpends Stage 1: Django app, three data adapters, working frontend." 83 files. This is the only TorontoSpends commit; everything from today is in it.
- This branch also carries Follow the Money's own Session 3/4 work (7 commits, `914b107`..`762bbb7`), already there before this session started — not TorontoSpends' concern, but relevant context for the PR (see Open questions).

**Working tree is clean as of this handoff.** Verify with `git status` on pickup — real risk that new local work (Supabase-adjacent scripts, further design tweaks) happened after this was written.

**Live services:**
- **Supabase**: real Postgres project linked, connection string in `torontospends/.env` (gitignored, not in the repo). Session pooler mode (IPv4-compatible; direct connection is IPv6-only on free tier). All data below lives here, not in a local sqlite copy.
- **Render**: decided (ADR-007) but **never actually deployed to**. Nothing is live on the public internet yet — everything has only ever been demoed via `manage.py runserver` on localhost.
- **GitHub Actions keepalive**: `.github/workflows/supabase-keepalive.yml` exists and is committed, but is **dormant** — it needs (1) this repo pushed to GitHub (done, see above) and (2) `DATABASE_URL` added as a repository secret (Settings → Secrets and variables → Actions) — **not done**, only the user can do this.

## Decisions

| Decision | Why | Reopen if |
|---|---|---|
| ADR-007 confirmed: separate Django/Postgres/HTMX stack, not Follow the Money's Python-batch/static-site stack | Two needs a static site can't cover: a human-review workflow for AI-extracted flags (Django admin gives this free) and live search/filtering across budget/contract/grant/entity records (needs a real query layer) | Not expected to reopen — this was deliberated, not a default |
| Hosting: Supabase (DB, free tier) + Render (app server, free tier pre-launch → must move to paid before the Oct 20–26 window) | Checked current 2026 free-tier terms live rather than assuming stale pricing. Free-tier Supabase pauses after 7 days with zero API/DB activity (confirmed real; a stuck connection almost masked this exact fact this session — see Dead ends). Render free tier has real cold-starts unacceptable during the live election window | If Render's free tier terms change, or if actual deploy (not yet done) surfaces a different constraint |
| Contract/grant/budget history bounded to Nov 2022–present (current council term) | Pre-existing decision from the scope doc, not made this session — carried forward | N/A, already settled |
| TMMIS backfill (Workstream A2) doesn't need a PDF pipeline for its Nov 2022–Oct 2025 window | Live-checked: the Bids Portal's award data is a structured CKAN dataset (`tobids-awarded-contracts`) with full history despite its own page claiming 18-month retention — 1,096 records fall in that window, zero PDFs needed | If the 18-month claim turns out to apply to the open-data export after all (check: do pre-2025 records disappear from the live API on a future pull?) |
| Non-competitive/>$30M awards also structured, not PDF | Separate CKAN dataset `tobids-non-competitive-contracts` covers these too (408 records in-window, includes awards to $57M+) | Only the >5yr-term slice remains untagged in either dataset — small, non-blocking gap |
| Grant program Oct 20 featured set: TAC, CSP, SNP, YVP (top 4 by dollar volume since 2022) | Live-checked against the real `community-grants-allocations` CKAN dataset. **Corrects the scope doc's own earlier guess that CSP was #1** — it's actually TAC, ~38% larger ($107.3M vs $78.0M) | If the underlying City dataset materially changes program totals on a future pull |
| `/methodology`, `/status`, `/corrections`, and the freshness pipeline deferred to post-launch | User's explicit call, made under a same-day demo deadline. `/status` specifically depends on the freshness pipeline's output, so deferring one defers the other | **Before any real public launch** — `/methodology` in particular needs to carry every caveat listed under "Must go on /methodology" below; this is not optional polish, it's the site's core editorial commitment carried over from Follow the Money |
| Design review done manually, not via the `/design-review` skill | That skill's fix loop auto-commits one commit per fix, which conflicts with this project's standing "commit only when explicitly asked" rule (confirmed multiple times this session). Applied the same audit rigor directly instead | If a future session is given explicit permission to let a skill auto-commit, this constraint lifts for that session only |
| Year-over-year budget "movers" restricted to programs with the *same name* in both 2022 and 2025, min $5M base | Some programs (e.g. "311 Toronto") were renamed/restructured between years — comparing them naively would show a fake ±100% swing that's an accounting artifact, not a funding decision. Checked live before building | If a program-renaming crosswalk is ever built, the comparison could widen beyond the current 36-of-~60 programs |

## Dead ends — don't retry

| Tried | What happened | Why it failed / fix |
|---|---|---|
| Row-by-row `Entity.objects.get_or_create()` per unique entity during the lobbying import | Worked fine against local sqlite, **never completed** against real Supabase — appeared to hang | Network round-trip latency × ~13,800 unique entities. Fixed by batch-resolving all entities in a handful of bulk queries first (`apps/entities/resolution.py`), then `bulk_create` everything. **Apply this pattern proactively for any future adapter that links rows to Entity** — don't rediscover this |
| Assuming a `bulk_create` timeout meant the new query was just slow | A prior *backgrounded and abandoned* run had left an `idle in transaction` connection on Supabase, holding a lock that blocked every subsequent write until Postgres's 2-minute `statement_timeout` fired | Checked `pg_stat_activity` directly, found the stuck session, `pg_terminate_backend()`'d it. **If a Supabase write mysteriously times out, check `pg_stat_activity` for a stuck session before assuming the query itself is slow** |
| Guessing field `max_length` values instead of checking real data first | Three separate `StringDataRightTruncation`/`DataError` failures mid-import: `communication_method` (real data has "Other:<free text>" tails to 140 chars, not a short category), `Ward` (city-wide grant programs list many wards comma-separated, up to 243 chars), `funding_program_code` (some rows carry a full program name instead of a short acronym, up to 60 chars) | Every one was caught by widening the field *after* checking the actual max length in the real data (never just picked a bigger number). **When adding a new CharField against a real external dataset, check actual max lengths in a sample before committing to a `max_length` value** |
| Automated browser click on the search input, testing HTMX live-search | Click didn't focus the input (`document.activeElement` stayed `BODY`); looked like a broken feature | This was the sandboxed browser-testing tool's viewport/click-mapping quirk, not a real site bug — confirmed by dispatching a real `keyup` event via JS directly, which worked correctly and returned real search results. **If browser-tool clicks don't seem to land, don't conclude the site is broken — verify via direct DOM/event dispatch before spending time "fixing" a non-bug** |
| The user's real Supabase DB password ended up in `.env.example` (the committed template) instead of `.env` (gitignored), with the password still wrapped in the template's `[...]` placeholder brackets | Caught before any commit — moved to `.env`, brackets stripped (they weren't part of the real password), `.env.example` restored to a placeholder, confirmed via `git check-ignore` | Not a dead end in the sense of wasted work, but a near-miss worth flagging: **always re-verify `.env.example` contains no real values before any commit that touches it** |

## Corrections & preferences
Carried forward from Follow the Money's own handoffs (still applicable here — same user, same repo):
- User is not deeply technical with devtools — give explicit step-by-step walkthroughs (this came up specifically for linking the Supabase connection string).
- Only commit when explicitly asked; user expects prompt action once they do ask (today: "lets commit, submit a pull request, then create a handoff doc" → all three executed directly, no re-confirmation needed).
- User answers quickly and decisively when a recommended option and its tradeoff are stated clearly (ADR-007 walkthrough, PR-scope question today both resolved in one round).
- User is comfortable with rapid re-prioritization under a deadline (deferred `/methodology`/`/status`/`/corrections`/freshness pipeline without hesitation once a demo deadline was set) — don't push back on scope cuts once they're stated, just execute cleanly and flag what's now missing.

New this session:
- **When a user-invoked skill's built-in behavior conflicts with a standing project rule (here: `/design-review`'s auto-commit-per-fix vs. "commit only when asked"), flag the conflict plainly and do the underlying work directly instead of either blindly running the skill or silently ignoring the invocation.** Confirmed twice this session (once for the homepage build, once for the design pass) — this is a stable pattern for this project, not a one-off.
- **Before recommending or building infrastructure (hosting tiers, keep-alive mechanisms, cron schedules), verify current behavior live rather than trusting training-era knowledge** — this repo's whole methodology (see Follow the Money's own decision log) is built around this, and it paid off concretely today: Supabase's actual free-tier pause mechanism, and whether direct DB queries vs. only REST calls count toward it, were both checked live rather than assumed, changing the keep-warm implementation.
- **User wants real, checked, defensible "interesting facts" on the homepage (e.g. year-over-year budget changes), not decorative stats.** The budget-movers feature explicitly excludes programs that don't have a clean same-name comparison across years, and states that exclusion on the page itself, rather than showing a bigger but partly-fake number.

## Work products

| Item | What it is | State |
|---|---|---|
| `torontospends/docs/00-scope.md` | Full Stage 1/2/3 scope, now with every open question from the original doc resolved | Committed, current |
| `torontospends/docs/08-decision-log.md` | **Read this first** — full narrative of every decision and bug this session, in far more detail than this handoff | Committed, current |
| `common/ckan_client.py`, `common/normalize_names.py` | Shared library, factored out of Follow the Money's `pipeline/` (which now imports from here instead of duplicating) | Committed, working |
| `torontospends/apps/{entities,budget,lobbying,grants,annotation}/` | The 5 Django apps | Committed, migrations applied to real Supabase |
| `apps/entities/resolution.py` | Batched entity-resolution helper (the fix for the Supabase-timeout dead end above) | Committed, used by both the lobbying and grants adapters |
| `apps/budget/management/commands/import_operating_budget.py` | Operating budget adapter | Committed, run: 78,978 lines loaded, FY2022–2025 |
| `apps/lobbying/management/commands/import_lobbying_registry.py` | Lobbying registry adapter (reads Follow the Money's already-ingested interim CSVs, not a fresh scrape) | Committed, run: 14,504 registrations, 140,921 communications |
| `apps/grants/management/commands/import_grants.py` | Community grants adapter | Committed, run: 6,511 rows, 3,183 recipient orgs |
| `apps/entities/management/commands/ping_supabase.py` | Keep-warm ping, tested working | Committed |
| `.github/workflows/supabase-keepalive.yml` | Scheduled ping, every 3 days | Committed but **dormant** — needs `DATABASE_URL` as a repo secret |
| `torontospends/templates/` | Homepage (hero stats, budget movers, 3 browse-card sections), search results, entity detail — Fraunces/Inter typography, per-domain color tags | Committed, verified rendering with no console errors, mobile table-overflow bug found and fixed |
| `torontospends/.env` | Real Supabase connection string | **Not in the repo** (gitignored) — exists only on this machine |
| Django admin | `/admin/`, username `admin`, password `dev-only-pw-12345` | **Change this before any public deployment** — flagged, not yet acted on |

## Must go on `/methodology` whenever it's built
Collected here so the next session doesn't have to re-mine `08-decision-log.md` for them:
- Revenue budget lines are stored as **negative** dollar amounts (a City accounting convention) — naively summing expenses+revenues does not produce Toronto's real net operating budget.
- Lobbying "contact" records show contact occurred at least once, **not** a ranked measure of lobbying intensity — the registry only logs what's voluntarily filed.
- Contract/grant/budget history is bounded to Nov 2022–present (current council term), an explicit editorial choice.
- The operating-budget dataset's own last refresh was 2026-02-25 — six months stale as of this session, and no FY2026 file exists yet.
- Budget "movers" comparison covers only the 36 (of ~60) programs with an unchanged name across 2022–2025; renamed/restructured programs are excluded, not silently zeroed.
- Of ~105 grant program codes, only 4 (TAC/CSP/SNP/YVP) get full review/feature treatment; the rest are ingested and searchable but not individually vetted.

## Verbatim
- Repo: `https://github.com/cmd-siri-bot/follow-the-money`, working dir `C:\Users\iamsi\toronto-2026-election`
- Branch: `developer-identity-extraction`, pushed, HEAD = `dc9e1fd`, matches `origin/developer-identity-extraction` exactly as of this handoff
- `main` is still well behind — this branch carries both Follow the Money's Session 3/4 work and all of TorontoSpends, unmerged
- Real row counts, all against live Supabase: 78,978 budget lines, 14,504 lobbying registrations, 140,921 lobbying communications, 6,511 grants, 24,190 entities (deduplicated across lobbying+grants via `org_key()` matching — less than the naive sum, confirming cross-referencing is genuinely working)

## Open questions
1. **PR was drafted but not confirmed created** — `gh` is installed but not authenticated in-session, so PR creation couldn't be completed by the assistant. The user was given (a) `gh auth login` to run themselves, or (b) a direct compare URL (`https://github.com/cmd-siri-bot/follow-the-money/compare/main...developer-identity-extraction`) with a ready title/description to paste in manually. **Check whether either happened before assuming a PR exists.**
2. **Render deployment has never been attempted.** ADR-007 settled on it, `.env.example` is ready, `requirements.txt` includes `gunicorn`/`whitenoise`, but the actual first deploy — env vars, `ALLOWED_HOSTS`, `DEBUG=False`, static files under Whitenoise, `CSRF_TRUSTED_ORIGINS` — is unstarted and was explicitly scoped out of tonight (local-only demo, by the user's own choice). First deploy of any stack tends to surface surprises; budget real time for it.
3. **Domain/DNS**: user mentioned owning a domain already, but nothing has been configured. Needs the user's own registrar access.
4. **Django admin's default password** (`dev-only-pw-12345`) needs changing before anything public.
5. **`/methodology`, `/status`, `/corrections`, freshness pipeline**: all deferred, all still fully unbuilt. See the dedicated section above for what `/methodology` specifically needs to carry.
6. Whether the demo itself (6pm today) went well, and whether anything was requested live during it that isn't reflected here.

## Next action
No single obviously-next task — depends entirely on how tonight's demo goes and what the user wants to prioritize afterward. Candidates, roughly in the order this session's own momentum suggests:
1. Confirm the PR actually exists (open question #1) and merge or continue iterating on it.
2. If the demo generated feedback, address that first — it's the freshest signal.
3. `/methodology`/`/status`/`/corrections` + freshness pipeline, since they were deferred, not cancelled, and are explicit Stage 1 scope.
4. First Render deploy, budgeting real time for first-deploy friction.

If a new chat picks this up: read `torontospends/docs/08-decision-log.md` first for full detail, then this file for the compressed version, then check `git log origin/developer-identity-extraction..HEAD` and `git status` to confirm nothing has drifted since this was written.
