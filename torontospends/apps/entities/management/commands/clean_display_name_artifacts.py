import re

from django.core.management.base import BaseCommand

from apps.entities.models import Entity

# Deliberately narrow: only fixes patterns confident enough to apply without a
# human eyeballing each one (match_key already ignores all of this via
# common/normalize_names.py's org_key(), so none of this ever affected entity
# matching -- it's display-only). Leaves ambiguous cases alone (e.g. "MC^2
# consulting Inc." or "Being~Inbetween" -- the symbol could be intentional
# stylization, not an artifact) rather than guessing.
_MULTI_SPACE_RE = re.compile(r" {2,}")


def clean(name: str) -> str:
    cleaned = _MULTI_SPACE_RE.sub(" ", name).strip()
    if cleaned.endswith("Inc.."):
        cleaned = cleaned[:-1]
    if cleaned.endswith("`"):
        cleaned = cleaned[:-1].rstrip()
    return cleaned


class Command(BaseCommand):
    help = "One-time cleanup of whitespace/stray-punctuation artifacts in Entity.display_name, found during the 2026-08-05 data review."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        changed = 0
        for entity in Entity.objects.all():
            new_name = clean(entity.display_name)
            if new_name != entity.display_name:
                self.stdout.write(f"{entity.display_name!r} -> {new_name!r}")
                changed += 1
                if not options["dry_run"]:
                    entity.display_name = new_name
                    entity.save(update_fields=["display_name"])
        self.stdout.write(self.style.SUCCESS(
            f"{'Would change' if options['dry_run'] else 'Changed'} {changed} entity name(s)."
        ))
