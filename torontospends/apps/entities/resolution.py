"""Batched entity resolution, shared by every data adapter that needs to
link rows to Entity rows without one DB round trip per row.

Extracted 2026-08-05 from import_lobbying_registry.py after that
command's original row-by-row Entity.objects.get_or_create() calls
worked fine against local sqlite but never completed against real
Supabase Postgres -- see docs/08-decision-log.md's 2026-08-05 "lobbying
import rewritten for remote Postgres" entry for the full story (a stuck
`idle in transaction` connection was part of it too, not just this).
Apply this proactively in new adapters rather than rediscovering the
same slowness.
"""
from .models import Entity

CHUNK = 1000


def chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def resolve_entities(needed: dict[tuple[str, str], str]) -> dict[tuple[str, str], Entity]:
    """needed: {(entity_type, match_key): display_name}. Returns the same
    keys mapped to real Entity rows -- existing ones fetched in bulk,
    missing ones bulk_created -- with zero per-row round trips."""
    resolved: dict[tuple[str, str], Entity] = {}

    for entity_type in (Entity.ORG, Entity.PERSON):
        keys = [k for k in needed if k[0] == entity_type]
        match_keys = [k[1] for k in keys]

        existing_by_match_key = {}
        for chunk in chunks(match_keys, CHUNK):
            for e in Entity.objects.filter(entity_type=entity_type, match_key__in=chunk):
                existing_by_match_key[e.match_key] = e

        to_create = []
        seen = set()
        for _, match_key in keys:
            if match_key in existing_by_match_key or match_key in seen:
                continue
            seen.add(match_key)
            to_create.append(Entity(
                entity_type=entity_type, match_key=match_key, display_name=needed[(entity_type, match_key)]
            ))
        for chunk in chunks(to_create, CHUNK):
            Entity.objects.bulk_create(chunk)
            for e in chunk:
                existing_by_match_key[e.match_key] = e

        for k in keys:
            resolved[k] = existing_by_match_key[k[1]]

    return resolved
