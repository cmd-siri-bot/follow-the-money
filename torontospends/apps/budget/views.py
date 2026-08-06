from collections import defaultdict

from django.db.models import Sum
from django.shortcuts import render

from .models import FactBudgetLine
from .taxonomy import (
    CATEGORY_ORDER,
    CATEGORY_PLAIN_ENGLISH,
    CITY_CONTROLLED_REVENUE_BUCKETS,
    POLICY_AREA_ORDER,
    PROPERTY_TAX_RATE_HISTORY,
    REVENUE_BUCKET_DESCRIPTIONS,
    REVENUE_BUCKET_ORDER,
    classify_revenue_bucket,
    normalize_program_name,
    policy_area_for_program,
    policy_area_hue,
)

LATEST_YEAR = 2025
EARLIEST_YEAR = 2022
PRIOR_YEAR = 2024
ALL_YEARS = [2022, 2023, 2024, 2025]

# Same threshold as the homepage's "budget movers" feature (apps/entities/views.py)
# -- below this, a tiny program's dollar change produces a noisy, meaningless
# percentage. Kept as a separate constant rather than a shared import to avoid
# a circular import between apps.entities.views and apps.budget.views.
MOVER_MIN_BASE_CENTS = 500_000_000  # $5M


def _bar_pct(value, max_value):
    return round(value / max_value * 100, 1) if max_value else 0


def policy_area_breakdown(year):
    rows = (
        FactBudgetLine.objects.filter(fiscal_year=year, expense_or_revenue="Expenses")
        .values("program").annotate(total=Sum("amount_cents"))
    )
    by_area = defaultdict(int)
    for r in rows:
        by_area[policy_area_for_program(r["program"])] += r["total"]
    total = sum(by_area.values()) or 1
    max_v = max(by_area.values()) if by_area else 0
    ordered = [a for a in POLICY_AREA_ORDER if a in by_area]
    return [
        {
            "name": a,
            "dollars": by_area[a] / 100,
            "pct_of_total": round(by_area[a] / total * 100, 1),
            "bar_pct": _bar_pct(by_area[a], max_v),
        }
        for a in ordered
    ]


def _spending_type_breakdown(year):
    rows = (
        FactBudgetLine.objects.filter(fiscal_year=year, expense_or_revenue="Expenses")
        .values("category_name").annotate(total=Sum("amount_cents"))
    )
    totals = {r["category_name"]: r["total"] for r in rows}
    total = sum(totals.values()) or 1
    max_v = max(totals.values()) if totals else 0
    out = []
    for cat in CATEGORY_ORDER:
        v = totals.get(cat, 0)
        label, desc = CATEGORY_PLAIN_ENGLISH[cat]
        out.append({
            "label": label,
            "description": desc,
            "dollars": v / 100,
            "pct_of_total": round(v / total * 100, 1),
            "bar_pct": _bar_pct(v, max_v),
        })
    return out


def _totals_by_normalized_program(year):
    rows = (
        FactBudgetLine.objects.filter(fiscal_year=year, expense_or_revenue="Expenses")
        .values("program").annotate(total=Sum("amount_cents"))
    )
    totals = defaultdict(int)
    display_name = {}
    for r in rows:
        norm = normalize_program_name(r["program"])
        totals[norm] += r["total"]
        display_name[norm] = r["program"]
    return totals, display_name


def _totals_by_normalized_program_and_category(year):
    """Same rollup as _totals_by_normalized_program, one level more granular
    -- by expenditure category_name, the City's own 9-value taxonomy that's
    confirmed stable across all four years (see taxonomy.py), unlike the
    free-text commitment_item field. Powers the per-program category
    breakdown on the YoY/since-2022 tables."""
    rows = (
        FactBudgetLine.objects.filter(fiscal_year=year, expense_or_revenue="Expenses")
        .values("program", "category_name").annotate(total=Sum("amount_cents"))
    )
    totals = defaultdict(int)
    for r in rows:
        norm = normalize_program_name(r["program"])
        totals[(norm, r["category_name"])] += r["total"]
    return totals


def _category_breakdown(norm, before_cat, after_cat):
    """What changed inside one program's total, broken down by category_name.
    Sized as a share of that program's own total movement (sum of |category
    changes|), not the site-wide max -- so a small program's bar chart isn't
    flattened to nothing next to Children's Services."""
    cats = {k[1] for k in before_cat if k[0] == norm} | {k[1] for k in after_cat if k[0] == norm}
    rows = []
    for cat in cats:
        b, a = before_cat.get((norm, cat), 0), after_cat.get((norm, cat), 0)
        if b == 0 and a == 0:
            continue
        label, _ = CATEGORY_PLAIN_ENGLISH.get(cat, (cat, ""))
        rows.append({
            "label": label,
            "before_dollars": b / 100,
            "after_dollars": a / 100,
            "change_dollars": (a - b) / 100,
        })
    rows.sort(key=lambda r: abs(r["change_dollars"]), reverse=True)
    max_abs = max((abs(r["change_dollars"]) for r in rows), default=0) or 1
    for r in rows:
        r["bar_pct"] = round(abs(r["change_dollars"]) / max_abs * 100, 1)
    return rows


def _program_changes(year_from, year_to):
    """Every comparable program's change between two years, using normalized
    names (see apps/budget/taxonomy.py) so cosmetic renames aren't reported
    as a cut plus a new program. Names not present in both years are
    reported as appeared/disappeared -- not guessed at, not hidden."""
    before, before_names = _totals_by_normalized_program(year_from)
    after, after_names = _totals_by_normalized_program(year_to)
    before_cat = _totals_by_normalized_program_and_category(year_from)
    after_cat = _totals_by_normalized_program_and_category(year_to)

    common = set(before) & set(after)
    changes = []
    for norm in common:
        b, a = before[norm], after[norm]
        if b <= 0:
            continue
        area = policy_area_for_program(after_names[norm])
        changes.append({
            "program": after_names[norm],
            "policy_area": area,
            "policy_area_hue": policy_area_hue(area),
            "before_dollars": b / 100,
            "after_dollars": a / 100,
            "change_dollars": (a - b) / 100,
            "pct_change": (a - b) / b * 100,
            "category_breakdown": _category_breakdown(norm, before_cat, after_cat),
        })
    changes.sort(key=lambda r: abs(r["change_dollars"]), reverse=True)

    movers_eligible = [c for c in changes if c["before_dollars"] * 100 >= MOVER_MIN_BASE_CENTS]
    by_pct = sorted(movers_eligible, key=lambda r: r["pct_change"], reverse=True)
    # Only genuine increases/decreases -- not just "the smallest of the increases"
    # padded in to fill 5 slots when almost everything grew (or shrank).
    pct_increases = [c for c in by_pct if c["pct_change"] > 0]
    pct_decreases = [c for c in by_pct if c["pct_change"] < 0]

    def _entry(program, dollars):
        area = policy_area_for_program(program)
        return {"program": program, "dollars": dollars, "policy_area": area, "policy_area_hue": policy_area_hue(area)}

    appeared = sorted(
        [_entry(after_names[n], after[n] / 100) for n in set(after) - set(before) if after[n] > 0],
        key=lambda r: -r["dollars"],
    )
    disappeared = sorted(
        [_entry(before_names[n], before[n] / 100) for n in set(before) - set(after) if before[n] > 0],
        key=lambda r: -r["dollars"],
    )

    return {
        "changes": changes,
        "top_pct_increases": pct_increases[:5],
        "top_pct_decreases": list(reversed(pct_decreases[-5:])),
        "appeared": appeared,
        "disappeared": disappeared,
        "comparable_count": len(changes),
    }


def _revenue_by_bucket(year):
    rows = (
        FactBudgetLine.objects.filter(fiscal_year=year, expense_or_revenue="Revenues")
        .values("commitment_item").annotate(total=Sum("amount_cents"))
    )
    by_bucket = defaultdict(int)
    for r in rows:
        # Revenue lines are stored as negative dollar amounts (City accounting
        # convention, see /methodology) -- flip sign so this page reads in
        # positive dollars like everything else on the site.
        by_bucket[classify_revenue_bucket(r["commitment_item"])] += -r["total"]
    return by_bucket


def revenue_breakdown_display(year):
    by_bucket = _revenue_by_bucket(year)
    total = sum(by_bucket.values()) or 1
    max_v = max(by_bucket.values()) if by_bucket else 0
    ordered = [b for b in REVENUE_BUCKET_ORDER if b in by_bucket]
    return [
        {
            "name": b,
            "description": REVENUE_BUCKET_DESCRIPTIONS[b],
            "dollars": by_bucket[b] / 100,
            "pct_of_total": round(by_bucket[b] / total * 100, 1),
            "bar_pct": _bar_pct(by_bucket[b], max_v),
        }
        for b in ordered
    ]


def _revenue_bucket_trend():
    per_year = {y: _revenue_by_bucket(y) for y in ALL_YEARS}
    out = []
    for b in REVENUE_BUCKET_ORDER:
        series = [per_year[y].get(b, 0) / 100 for y in ALL_YEARS]
        pct_change = round((series[-1] - series[0]) / series[0] * 100, 1) if series[0] else None
        out.append({
            "name": b,
            "dollars_2022": series[0],
            "dollars_2025": series[-1],
            "change_dollars": series[-1] - series[0],
            "pct_change_since_2022": pct_change,
        })
    out.sort(key=lambda r: r["dollars_2025"], reverse=True)
    return out


def overview(request):
    revenue_trend = _revenue_bucket_trend()
    context = {
        "latest_year": LATEST_YEAR,
        "prior_year": PRIOR_YEAR,
        "earliest_year": EARLIEST_YEAR,
        "policy_areas": policy_area_breakdown(LATEST_YEAR),
        "spending_types": _spending_type_breakdown(LATEST_YEAR),
        "yoy": _program_changes(PRIOR_YEAR, LATEST_YEAR),
        "since_2022": _program_changes(EARLIEST_YEAR, LATEST_YEAR),
        "revenue_breakdown": revenue_breakdown_display(LATEST_YEAR),
        "revenue_trend": revenue_trend,
        "property_tax_trend": next((r for r in revenue_trend if r["name"] == "Property Tax"), None),
        "tax_rate_history": PROPERTY_TAX_RATE_HISTORY,
    }
    return render(request, "budget/overview.html", context)


# --- Reusable helpers, also used by the homepage (apps.entities.views) ---
# Parameterized by year rather than hardcoded to EARLIEST_YEAR/LATEST_YEAR, since
# the homepage needs a 2023-2025 window (the mayoral-transition reference point)
# distinct from this page's own 2022-2025 default.

def _policy_area_totals(year):
    rows = (
        FactBudgetLine.objects.filter(fiscal_year=year, expense_or_revenue="Expenses")
        .values("program").annotate(total=Sum("amount_cents"))
    )
    by_area = defaultdict(int)
    for r in rows:
        by_area[policy_area_for_program(r["program"])] += r["total"]
    return by_area


def policy_area_changes(year_from, year_to):
    """Policy-area-level spending change between two years -- coarser than
    _program_changes' per-program table, sized for a homepage summary
    rather than a full data page."""
    before = _policy_area_totals(year_from)
    after = _policy_area_totals(year_to)
    rows = []
    for area in POLICY_AREA_ORDER:
        b, a = before.get(area, 0), after.get(area, 0)
        if b <= 0:
            continue
        rows.append({
            "name": area,
            "hue": policy_area_hue(area),
            "before_dollars": b / 100,
            "after_dollars": a / 100,
            "change_dollars": (a - b) / 100,
            "pct_change": (a - b) / b * 100,
        })
    rows.sort(key=lambda r: r["change_dollars"], reverse=True)
    return rows


def revenue_bucket_trend_since(start_year, end_year=LATEST_YEAR):
    per_year = {y: _revenue_by_bucket(y) for y in (start_year, end_year)}
    out = []
    for b in REVENUE_BUCKET_ORDER:
        before = per_year[start_year].get(b, 0) / 100
        after = per_year[end_year].get(b, 0) / 100
        pct_change = round((after - before) / before * 100, 1) if before else None
        out.append({
            "name": b,
            "description": REVENUE_BUCKET_DESCRIPTIONS[b],
            "dollars_before": before,
            "dollars_after": after,
            "change_dollars": after - before,
            "pct_change": pct_change,
            "city_controlled": b in CITY_CONTROLLED_REVENUE_BUCKETS,
        })
    out.sort(key=lambda r: r["dollars_after"], reverse=True)
    return out


def property_tax_cumulative_rate_since(start_year):
    """Compounds Council-approved rate increases (PROPERTY_TAX_RATE_HISTORY)
    for years AFTER start_year -- the rate approved *in* start_year is the
    increase into that year, not since it, so it's excluded from the product."""
    multiplier = 1.0
    included_years = []
    for entry in PROPERTY_TAX_RATE_HISTORY:
        if entry["year"] > start_year:
            multiplier *= 1 + entry["increase_pct"] / 100
            included_years.append(entry)
    return {"cumulative_pct": round((multiplier - 1) * 100, 1), "years": included_years}
