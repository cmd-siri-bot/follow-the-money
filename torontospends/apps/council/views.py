from functools import reduce

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.shortcuts import render

from .models import AgendaItem
from .taxonomy import expand_query

RESULT_LIMIT = 25


def search(request):
    """Extractive search over AgendaItem -- no LLM synthesis yet (see the
    project's council-archive plan: that's a separate, cost-gated step).
    Returns the actual official tracking_status_text/decision_text
    verbatim, plus any curated NewsCitations, so every word shown already
    traces to a source."""
    query = (request.GET.get("q") or "").strip()
    results = []
    if query:
        terms = expand_query(query)
        search_query = reduce(lambda a, b: a | b, (SearchQuery(t) for t in terms))
        vector = (
            SearchVector("title", weight="A")
            + SearchVector("tracking_status_text", weight="A")
            + SearchVector("summary_text", weight="B")
            + SearchVector("decision_text", weight="B")
        )
        results = list(
            AgendaItem.objects.annotate(search=vector, rank=SearchRank(vector, search_query))
            .filter(search=search_query)
            .order_by("-rank")
            .prefetch_related("news_citations")[:RESULT_LIMIT]
        )
    return render(request, "council/search.html", {"query": query, "results": results})
