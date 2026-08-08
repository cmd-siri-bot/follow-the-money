"""Hand-curated aliases for council/committee search -- same discipline as
apps/budget/taxonomy.py's PROGRAM_ALIASES: small, documented, verified,
not guessed at scale.

A public nickname for a policy issue (e.g. "rain tax") often never
appears in the official decision text, which uses formal language (e.g.
"stormwater charge"). Rather than building semantic/embedding search for
this (see /methodology and the project plan), v1 keeps a short, explicit
list of nickname -> keyword mappings, seeded for whatever issues this
site's pilot and follow-up coverage actually reaches. Extend this list
only after confirming the keywords actually appear in real ingested
AgendaItem text -- an unverified alias just silently returns nothing.
"""

TOPIC_ALIASES = {
    # Verified 2026-08-06 against real Executive Committee items (e.g.
    # 2025.EX20.12 "Reducing Stormwater Runoff and Mitigating Basement
    # Flooding") -- the official record never says "rain tax," but does
    # say "stormwater charge" / "stormwater runoff" / "basement flooding."
    "rain tax": ["stormwater charge", "stormwater runoff", "stormwater management"],
}


def expand_query(query: str) -> list[str]:
    """The original query plus any keyword expansions from a matched
    alias. Callers OR these together in search rather than replacing the
    original query, so an exact hit on the nickname itself (e.g. if a
    news citation or future item literally uses the word) still works."""
    q = query.strip().lower()
    terms = [query]
    for alias, keywords in TOPIC_ALIASES.items():
        if alias in q or q in alias:
            terms.extend(keywords)
    return terms
