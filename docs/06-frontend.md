# 06 — Frontend

**Do not start this before Phase 3 produces a number.** The design should be built around the actual finding. If the correlation is null, the hero is a different page entirely and anything built speculatively gets thrown away.

---

## The one job

A visitor should understand the finding in eight seconds and be able to interrogate it for twenty minutes.

That ordering matters. Answer first, explore second. The three existing Toronto council sites all invert this — they open with a search box, which asks the visitor to already know what they're looking for.

---

## Design direction

Two things to avoid. First, the civic-tech default: blue-grey, Inter, card grid, faintly municipal. It signals "volunteer dashboard" and undercuts the analytical claim. Second, the AI-generated default: cream background, high-contrast serif, terracotta accent. Both are places to not spend the design budget.

**Ground it in the subject's own materials.** The vernacular here is the planning document — zoning schedules, development application signage, the yellow public notice board bolted to a construction hoarding, survey plans, the typography of municipal legal notices. That world has a real visual language: monospaced application numbers, hairline survey linework, stamped approval marks, the specific bureaucratic ugliness of a rezoning notice. It's underused and it's *specific to this piece*.

**Signature element:** a single scroll-driven sequence in the hero that moves from one donation record → to the cluster it belongs to → to the councillor → to the vote. One concrete, named, real path through the data, using actual values from the dataset. Every abstraction the project makes is legible in that one chain. Spend the boldness there and keep everything below it quiet.

**Type:** a display face with some institutional weight paired with a genuine monospace for all data — amounts, dates, application numbers, ward numbers. The monospace isn't decorative; it's how planning documents actually set reference numbers, and it makes columns of dollar figures scannable.

**Motion:** the hero sequence, and nothing else. Respect `prefers-reduced-motion` with a static fallback that still tells the whole chain.

Before building, write out the token system — 4–6 named hex values, three type roles, a layout concept — and check each choice against "would I have made this for any civic data project?" If yes, change it.

---

## Information architecture

**1. Hero — the finding.**
One sentence stating the result, in plain language, with the interval. Then the scroll sequence. No search box above the fold.

**2. The scatter.**
x = development-linked contribution share, y = pro-development vote rate. One point per councillor. Hover for name and values. Include the confidence band and make the leave-one-out toggle available right here — showing that the result survives (or doesn't survive) dropping any single member, inline, is a strong move.

**3. Councillor cards.**
26 + mayor. Per card: donor mix, vote record on development items, top donors with basis strings visible, ward context, absence rate. **The `basis` string is the feature** — a visitor clicking a donor and seeing "flagged: 4 donors at same commercial address, all within 6 days, all at limit" is what makes the whole thing credible.

**4. Ward map.**
Choropleth toggling between development-dollar intensity and approval rate. This is the confounder made visible — if the two maps look identical, the visitor sees the ward-composition problem for themselves before anyone has to explain it.

**5. Methodology.**
Full page, per `docs/04`. Linked from the hero, not buried in a footer.

**6. Downloads.**
Every processed CSV, plus the repo link.

---

## Copy rules

These are load-bearing and non-negotiable — see `docs/07`.

- **Never a causal verb.** "Correlates with," "is associated with." Never "buys," "influences," "leads to." Not in headlines, not in chart titles, not in tooltips.
- **Never impute motive** to a named individual, councillor or donor.
- State that contributions are **legal, disclosed, and capped** early and visibly, not as a footnote.
- Chart titles describe what is plotted, not what it means.
- Uncertainty appears in the copy, not just in the error bars.

Write from the reader's side: "how much of this councillor's funding came from people linked to development" beats "development affiliation score distribution."

---

## Stack

- **Astro** (or Next.js static export) — content-heavy with islands of interactivity is exactly Astro's shape
- **Observable Plot** for the scatter and distributions; D3 only if Plot can't do it
- **MapLibre GL** with the ward GeoJSON
- Static host, any CDN
- All data as static JSON in `site/public/data/`. **The frontend computes nothing** — every number comes from the pipeline.

## Quality floor

Responsive to mobile (the scatter needs a real small-screen treatment, not a squeeze). Visible keyboard focus. Reduced motion respected. Every chart has a text alternative stating the finding. Total page weight under 500KB before the map tiles.

## Explicitly out of scope for v1

2026 candidate contribution data (not filed until spring 2027), real-time vote updates, other municipalities, third-party advertiser analysis, user accounts, anything with a login.
