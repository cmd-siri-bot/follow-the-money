# 00 — Getting Started (Phase 0: Feasibility)

**Goal of this phase:** find out whether the project is buildable before investing a weekend in it. Ends with a written go/no-go.
**Time budget:** ~3 hours. If you're past 5, stop and reassess.
**Deliverable:** a `phase0-findings.md` and a scope decision logged in `docs/08-decision-log.md`.

---

## Step 1 — Scaffold the repo (15 min)

```bash
mkdir -p follow-the-ask/{data/{raw,interim,processed},pipeline,notebooks,site,docs}
cd follow-the-ask
git init
python -m venv .venv && source .venv/bin/activate
pip install requests pandas jupyter python-dotenv beautifulsoup4 playwright
```

Add a `.gitignore` that excludes `.venv/` and `data/raw/` (raw files can be large and are always re-fetchable). **Commit `data/processed/` — those are the published artifacts.**

Drop the `docs/` folder from this package into the repo root and commit. The strategy doc travels with the code.

## Step 2 — Confirm the vote record resolves (20 min)

This is already verified as live, but confirm the schema before designing anything around it.

```python
import requests, pandas as pd

BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action"
VOTES_2022_2026 = "55ead013-2331-4686-9895-9e8145b94189"

r = requests.get(f"{BASE}/datastore_search",
                 params={"resource_id": VOTES_2022_2026, "limit": 100}).json()

print(r["result"]["total"])
df = pd.DataFrame(r["result"]["records"])
print(df.columns.tolist())
df.head(20)
```

**What you're looking for:**
- Total row count (expect tens of thousands — one row per member per recorded vote)
- Whether there's a stable agenda item reference (something like `Agenda Item #` — this is your join key to development applications, and everything depends on it existing)
- How motions are described, and whether the text is rich enough to classify from
- Whether vote values are exactly `Yes` / `No` / `Absent` as documented

Also pull the readme resource `6f7d8bb7-6ae4-4a15-8b01-b95a81c35dfe` — it's the City Clerk's own field documentation and will save you guessing.

**Red flag:** if there's no agenda item identifier linking a vote to a specific matter, the whole join collapses and you fall back to classifying from motion text alone. Note it and continue; it's survivable but it degrades precision.

## Step 3 — Spike the EFD scraper (60–90 min) ⚠️ *the real gate*

This is the step that decides the project. Everything else is known-easy.

Go to `app.toronto.ca/EFD` in a browser with devtools open. Search for one 2022 councillor candidate. Watch the network tab.

**Answer these five questions and write them down:**

1. Is the contribution list rendered server-side in HTML, or fetched via XHR? (XHR means there's an undocumented JSON endpoint, which makes this trivial — check first.)
2. Does JSF require a session token / ViewState that has to be carried between requests? (This is the usual pain point with JSF apps.)
3. Is there a stable URL pattern per candidate, or is navigation entirely POST-driven?
4. Is the contribution list paginated, and how?
5. What fields are exposed per contribution — name, address, amount, date? **Date and address are both essential.** Without dates you lose temporal clustering; without addresses you lose the strongest employer signal. If either is missing, the method in `docs/02` needs rethinking before you go further.

Then write a scraper for one candidate only. Don't generalize yet.

**Decision point:**
- Clean JSON endpoint found → full scope, all 26 seats, proceed happily
- Scrapeable with effort → full scope, budget a day for the scraper
- Hostile (heavy ViewState, captcha, rate limiting) → **reduce scope**: mayor plus 10 wards, chosen by development application volume rather than by anything that looks like political selection. Document the selection rule.

## Step 4 — Confirm the supporting datasets (30 min)

Search the catalogue for each, and for each one record the package slug, the resource ID you'll use, whether `datastore_active` is true, and the date coverage.

```python
for q in ["lobbyist registry", "development applications",
          "committee of adjustment", "ward boundaries"]:
    res = requests.get(f"{BASE}/package_search", params={"q": q, "rows": 5}).json()
    for p in res["result"]["results"]:
        print(q, "|", p["name"])
```

The one that matters most: **development applications must cover 2022–2026 and must carry a ward field.** If the coverage window is short or ward is missing, note it in the decision log.

## Step 5 — Write the go/no-go (20 min)

A short `phase0-findings.md`, in the repo:

- What resolved, what didn't
- The EFD verdict and the scope decision that follows from it
- Whether the vote↔agenda item join key exists
- Whether contribution records carry both date and address
- Revised time estimate
- Anything that surprised you

Copy the decisions into `docs/08-decision-log.md`.

---

## Order of operations, and why

Do **Step 3 before Step 4**. The supporting datasets are almost certainly fine; the EFD scrape is the coin flip. Front-load the thing that can kill the project. If Step 3 fails badly, you've spent 90 minutes finding that out rather than a weekend.

## What Phase 0 explicitly does not include

No classification. No analysis. No design. No writing. The temptation will be to start building the donor classifier because it's the interesting part — resist it until you know you can get the donors.

## Handing this to Claude

Starting a build session, open with roughly:

> Read STRATEGY.md and docs/00-getting-started.md in this repo. We're at Phase 0, Step 3 — spiking the EFD scraper. Here's what devtools shows me: [paste]. Don't generalize the scraper yet, just get one candidate's contribution list into a DataFrame and tell me what fields we actually have.

Keep sessions scoped to one step. The decision log is what carries context between them.
