from django.db.models import Count, Max, Min, Q, Sum
from django.shortcuts import get_object_or_404, render

from apps.annotation.models import Correction
from apps.budget.models import FactBudgetLine
from apps.budget.taxonomy import (
    MAYORAL_TRANSITION_NOTE,
    MAYORAL_TRANSITION_SOURCE,
    MAYORAL_TRANSITION_YEAR,
    TORONTO_POPULATION_2021_CENSUS,
    TORONTO_POPULATION_SOURCE_URL,
)
from apps.budget.views import (
    LATEST_YEAR as LATEST_BUDGET_YEAR,
    policy_area_breakdown,
    policy_area_changes,
    property_tax_cumulative_rate_since,
    revenue_bucket_trend_since,
    revenue_breakdown_display,
)
from apps.grants.models import FactGrant
from apps.lobbying.models import FactLobbyingCommunication, FactLobbyingRegistration

from .models import Entity

RESULT_LIMIT = 25
EARLIEST_BUDGET_YEAR = 2022
FEATURED_GRANT_PROGRAM_CODES = ["TAC", "CSP", "SNP", "YVP"]  # top 4 by dollar volume, per docs/08-decision-log.md's 2026-08-05 grant-cut decision


def _the_big_picture():
    """Total 2025 expenses, revenue, and net position -- the broad
    overview a first-time visitor needs before anything else on the page
    means much."""
    total_expense_cents = FactBudgetLine.objects.filter(
        fiscal_year=LATEST_BUDGET_YEAR, expense_or_revenue="Expenses"
    ).aggregate(t=Sum("amount_cents"))["t"] or 0
    total_revenue_cents = -(FactBudgetLine.objects.filter(
        fiscal_year=LATEST_BUDGET_YEAR, expense_or_revenue="Revenues"
    ).aggregate(t=Sum("amount_cents"))["t"] or 0)
    return {
        "total_budget_dollars": total_expense_cents / 100,
        "total_revenue_dollars": total_revenue_cents / 100,
        "net_dollars": (total_revenue_cents - total_expense_cents) / 100,
        "cost_per_resident": round((total_expense_cents / 100) / TORONTO_POPULATION_2021_CENSUS),
        "population": TORONTO_POPULATION_2021_CENSUS,
        "population_source_url": TORONTO_POPULATION_SOURCE_URL,
    }


def _tax_bill_context():
    """Property tax specifically, since 2023 -- the mayoral-term reference
    point requested for the homepage, distinct from /budget's 2022 default."""
    trend = revenue_bucket_trend_since(MAYORAL_TRANSITION_YEAR)
    property_tax = next(r for r in trend if r["name"] == "Property Tax")
    rate = property_tax_cumulative_rate_since(MAYORAL_TRANSITION_YEAR)
    return {
        "property_tax": property_tax,
        "rate": rate,
        "mayoral_transition_year": MAYORAL_TRANSITION_YEAR,
        "mayoral_transition_note": MAYORAL_TRANSITION_NOTE,
        "mayoral_transition_source": MAYORAL_TRANSITION_SOURCE,
    }


def _what_else_costs_more():
    """Other City-controlled revenue (user fees, water/waste fees, other
    taxes, fines) since 2023 -- property tax is covered separately above,
    so excluded here. Provincial/federal transfers, reserve drawdowns,
    and investment income are deliberately left out: the City doesn't set
    those rates, so they don't answer "what am I paying more of.\""""
    trend = revenue_bucket_trend_since(MAYORAL_TRANSITION_YEAR)
    return [r for r in trend if r["city_controlled"] and r["name"] != "Property Tax"]


def _where_new_money_went():
    """Policy-area-level spending change since 2023 -- coarser than
    /budget's per-program tables, sized for a homepage summary. Only
    genuine decreases are shown as decreases -- not just "the smallest
    increases" padded in to fill a fixed slot count, which would be
    misleading in a window where almost every area grew."""
    changes = policy_area_changes(MAYORAL_TRANSITION_YEAR, LATEST_BUDGET_YEAR)
    increases = [c for c in changes if c["change_dollars"] > 0][:5]
    decreases = sorted([c for c in changes if c["change_dollars"] < 0], key=lambda r: r["change_dollars"])[:5]
    return {"increases": increases, "decreases": decreases}


def _browse_context():
    """Curated entry points further down the homepage: the highest-dollar-
    volume budget programs, the most-lobbied-for organizations, and the
    biggest grant programs, so a visitor has something to click before
    they have to know what to search for."""
    top_programs = list(
        FactBudgetLine.objects.filter(fiscal_year=LATEST_BUDGET_YEAR, expense_or_revenue="Expenses")
        .values("program")
        .annotate(total_cents=Sum("amount_cents"))
        .order_by("-total_cents")[:9]
    )
    for p in top_programs:
        p["total_dollars"] = p["total_cents"] / 100

    top_lobbied_orgs = (
        FactLobbyingRegistration.objects.exclude(beneficiary__isnull=True)
        .values("beneficiary__id", "beneficiary__display_name")
        .annotate(n=Count("id"))
        .order_by("-n")[:9]
    )

    top_grant_programs = list(
        FactGrant.objects.filter(funding_program_code__in=FEATURED_GRANT_PROGRAM_CODES)
        .values("funding_program_code", "funding_program_name")
        .annotate(total_cents=Sum("amount_cents"), n=Count("id"))
        .order_by("-total_cents")
    )
    for g in top_grant_programs:
        g["total_dollars"] = g["total_cents"] / 100

    total_grant_cents = FactGrant.objects.aggregate(t=Sum("amount_cents"))["t"] or 0

    return {
        "top_programs": top_programs,
        "top_lobbied_orgs": top_lobbied_orgs,
        "top_grant_programs": top_grant_programs,
        "latest_budget_year": LATEST_BUDGET_YEAR,
        "earliest_budget_year": EARLIEST_BUDGET_YEAR,
        "total_grant_dollars": total_grant_cents / 100,
        "lobbying_registration_count": FactLobbyingRegistration.objects.count(),
    }


def _home_context():
    context = {
        "latest_budget_year": LATEST_BUDGET_YEAR,
        "big_picture": _the_big_picture(),
        "policy_areas": policy_area_breakdown(LATEST_BUDGET_YEAR),
        "revenue_breakdown": revenue_breakdown_display(LATEST_BUDGET_YEAR),
        "tax_bill": _tax_bill_context(),
        "other_costs": _what_else_costs_more(),
        "funding_changes": _where_new_money_went(),
    }
    context.update(_browse_context())
    return context


def search(request):
    query = (request.GET.get("q") or "").strip()

    if not query:
        context = _home_context()
        template = "home/_fragment.html" if request.htmx else "home/index.html"
        return render(request, template, context)

    entities = Entity.objects.filter(
        Q(display_name__icontains=query)
    ).order_by("display_name")[:RESULT_LIMIT]

    budget_lines = FactBudgetLine.objects.filter(
        Q(program__icontains=query)
        | Q(service__icontains=query)
        | Q(commitment_item__icontains=query)
        | Q(category_name__icontains=query)
    ).order_by("-fiscal_year")[:RESULT_LIMIT]

    registrations = FactLobbyingRegistration.objects.select_related(
        "registrant", "beneficiary", "firm"
    ).filter(
        Q(subject_matter__icontains=query)
        | Q(particulars__icontains=query)
        | Q(registrant__display_name__icontains=query)
        | Q(beneficiary__display_name__icontains=query)
        | Q(firm__display_name__icontains=query)
    ).order_by("-effective_date")[:RESULT_LIMIT]

    grants = FactGrant.objects.select_related("recipient").filter(
        Q(recipient_name_raw__icontains=query)
        | Q(funding_program_name__icontains=query)
        | Q(funding_program_code__icontains=query)
        | Q(division__icontains=query)
    ).order_by("-fiscal_year")[:RESULT_LIMIT]

    context = {
        "query": query,
        "entities": entities,
        "budget_lines": budget_lines,
        "registrations": registrations,
        "grants": grants,
        "has_results": bool(entities or budget_lines or registrations or grants),
    }

    # HTMX live-search requests only need the results fragment re-swapped
    # into #page-content -- a full page reload would double-wrap <header>/<main>.
    template = "search/_results_fragment.html" if request.htmx else "search/results.html"
    return render(request, template, context)


def entity_detail(request, entity_id):
    entity = get_object_or_404(Entity, pk=entity_id)

    registrations_as_registrant = FactLobbyingRegistration.objects.select_related("beneficiary", "firm").filter(
        registrant=entity
    ).order_by("-effective_date")
    registrations_as_beneficiary = FactLobbyingRegistration.objects.select_related("registrant", "firm").filter(
        beneficiary=entity
    ).order_by("-effective_date")
    registrations_as_firm = FactLobbyingRegistration.objects.select_related("registrant", "beneficiary").filter(
        firm=entity
    ).order_by("-effective_date")

    communications_as_poh = FactLobbyingCommunication.objects.select_related("registration").filter(
        poh_entity=entity
    ).order_by("-communication_date")[:RESULT_LIMIT]
    communications_as_lobbyist = FactLobbyingCommunication.objects.select_related("registration").filter(
        lobbyist_entity=entity
    ).order_by("-communication_date")[:RESULT_LIMIT]

    grants_received = FactGrant.objects.filter(recipient=entity).order_by("-fiscal_year")

    context = {
        "entity": entity,
        "registrations_as_registrant": registrations_as_registrant,
        "registrations_as_beneficiary": registrations_as_beneficiary,
        "registrations_as_firm": registrations_as_firm,
        "communications_as_poh": communications_as_poh,
        "communications_as_lobbyist": communications_as_lobbyist,
        "grants_received": grants_received,
    }
    return render(request, "entities/detail.html", context)


# Every dataset the site publishes, for /status -- pulled from the
# retrieved_at already stamped on every SourcedFact row rather than a
# separate freshness table, since that timestamp is the actual freshness
# signal and duplicating it would just be a second place to go stale.
DATASETS = [
    {
        "label": "Operating budget",
        "queryset": FactBudgetLine.objects,
        "source_url": "https://open.toronto.ca/dataset/budget-operating-budget-program-summary-by-expenditure-category/",
        "known_issue": "The City's own file was last refreshed 2026-02-25, and no FY2026 file has been published yet -- this site can't be fresher than its source.",
    },
    {
        "label": "Lobbying registrations",
        "queryset": FactLobbyingRegistration.objects,
        "source_url": "https://open.toronto.ca/dataset/lobbyist-registry/",
        "known_issue": "",
    },
    {
        "label": "Lobbying communications",
        "queryset": FactLobbyingCommunication.objects,
        "source_url": "https://open.toronto.ca/dataset/lobbyist-registry/",
        "known_issue": "",
    },
    {
        "label": "Community grants",
        "queryset": FactGrant.objects,
        "source_url": "https://open.toronto.ca/dataset/community-grants-allocations/",
        "known_issue": "",
    },
]


def status(request):
    datasets = []
    for d in DATASETS:
        agg = d["queryset"].aggregate(latest=Max("retrieved_at"), earliest=Min("retrieved_at"), row_count=Count("id"))
        datasets.append({**d, **agg})
    return render(request, "status.html", {"datasets": datasets})


def methodology(request):
    return render(request, "methodology.html", {"datasets": DATASETS})


def corrections(request):
    corrections_list = Correction.objects.filter(published=True)
    return render(request, "corrections.html", {"corrections": corrections_list})
