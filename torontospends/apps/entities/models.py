import sys
from pathlib import Path

from django.db import models

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from common.normalize_names import org_key, normalize_name  # noqa: E402


class Entity(models.Model):
    """A resolved org or person that appears across budget, contract,
    grant, and lobbying data. match_key is how records get merged --
    org_key() for organizations (same merge logic Follow the Money's
    knowledge graph uses), normalize_name()'s match_key for people.
    """

    ORG = "org"
    PERSON = "person"
    ENTITY_TYPE_CHOICES = [(ORG, "Organization"), (PERSON, "Person")]

    entity_type = models.CharField(max_length=10, choices=ENTITY_TYPE_CHOICES)
    display_name = models.CharField(max_length=500)
    match_key = models.CharField(max_length=500, db_index=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["entity_type", "match_key"])]
        verbose_name_plural = "entities"

    def __str__(self):
        return self.display_name

    @staticmethod
    def compute_match_key(entity_type: str, name: str) -> str:
        if entity_type == Entity.ORG:
            return org_key(name)
        return normalize_name(name)["match_key"]


class SourcedFact(models.Model):
    """Abstract base for every fact_* row in the schema (docs/00-scope.md
    §4): every fact row must trace back to where it came from and when it
    was fetched -- no number goes on the site without both, per this
    project's own editorial standard.
    """

    source_url = models.URLField(max_length=1000)
    retrieved_at = models.DateTimeField()

    class Meta:
        abstract = True


class RawRecord(models.Model):
    """Staging table: the as-fetched payload before any transformation,
    kept per this project's 'archive the raw' discipline (established in
    Follow the Money -- every fact needs to be re-derivable from what was
    actually retrieved, not just the transformed result).
    """

    source_system = models.CharField(max_length=200)
    source_url = models.URLField(max_length=1000)
    retrieved_at = models.DateTimeField()
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["source_system", "processed"])]

    def __str__(self):
        return f"{self.source_system} @ {self.retrieved_at:%Y-%m-%d}"
