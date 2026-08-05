from collections import defaultdict

from django.db.models import Sum
from django.shortcuts import render

from .models import FactBudgetLine
from .taxonomy import (
    CATEGORY_ORDER,
    CATEGORY_PLAIN_ENGLISH,
    POLICY_AREA_ORDER,
    PROPERTY_TAX_RATE_HISTORY,
    REVENUE_BUCKET_DESCRIPTIONS,
    REVENUE_BUCKET_ORDER,
    classify_revenue_bucket,
    normalize_program_name,
    policy_area_for_program,
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


def _policy_area_breakdown(year):
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


def _program_changes(year_from, year_to):
    """Every comparable program's change between two years, using normalized
    names (see apps/budget/taxonomy.py) so cosmetic renames aren't reported
    as a cut plus a new program. Names not present in both years are
    reported as appeared/disappeared -- not guessed at, not hidden."""
    before, before_names = _totals_by_normalized_program(year_from)
    after, after_names = _totals_by_normalized_program(year_to)

    common = set(before) & set(after)
    changes = []
    for norm in common:
        b, a = before[norm], after[norm]
        if b <= 0:
            continue
        changes.append({
            "program": after_names[norm],
            "policy_area": policy_area_for_program(after_names[norm]),
            "before_dollars": b / 100,
            "after_dollars": a / 100,
            "change_dollars": (a - b) / 100,
            "pct_change": (a - b) / b * 100,
        })
    changes.sort(key=lambda r: abs(r["change_dollars"]), reverse=True)

    movers_eligible = [c for c in changes if c["before_dollars"] * 100 >= MOVER_MIN_BASE_CENTS]
    by_pct = sorted(movers_eligible, key=lambda r: r["pct_change"], reverse=True)

    appeared = sorted(
        [
            {"program": after_names[n], "dollars": after[n] / 100, "policy_area": policy_area_for_program(after_names[n])}
            for n in set(after) - set(before) if after[n] > 0
        ],
        key=lambda r: -r["dollars"],
    )
    disappeared = sorted(
        [
            {"program": before_names[n], "dollars": before[n] / 100, "policy_area": policy_area_for_program(before_names[n])}
            for n in set(before) - set(after) if before[n] > 0
        ],
        key=lambda r: -r["dollars"],
    )

    return {
        "changes": changes,
        "top_pct_increases": by_pct[:5],
        "top_pct_decreases": list(reversed(by_pct[-5:])) if len(by_pct) >= 5 else [],
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


def _revenue_breakdown(year):
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
        "policy_areas": _policy_area_breakdown(LATEST_YEAR),
        "spending_types": _spending_type_breakdown(LATEST_YEAR),
        "yoy": _program_changes(PRIOR_YEAR, LATEST_YEAR),
        "since_2022": _program_changes(EARLIEST_YEAR, LATEST_YEAR),
        "revenue_breakdown": _revenue_breakdown(LATEST_YEAR),
        "revenue_trend": revenue_trend,
        "property_tax_trend": next((r for r in revenue_trend if r["name"] == "Property Tax"), None),
        "tax_rate_history": PROPERTY_TAX_RATE_HISTORY,
    }
    return render(request, "budget/overview.html", context)
