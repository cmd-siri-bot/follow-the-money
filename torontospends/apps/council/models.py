from django.db import models

from apps.entities.models import SourcedFact


class Meeting(SourcedFact):
    """One sitting of City Council or a Committee/Community Council, per
    TMMIS (app.toronto.ca/tmmis). tmmis_meeting_id matches the City's own
    format, e.g. "2025.CC26" or "2025.EX20" -- kept as the natural key
    since it's how every agenda item links back to where it was heard.
    """

    COUNCIL = "council"
    STANDING_COMMITTEE = "standing_committee"
    COMMUNITY_COUNCIL = "community_council"
    SPECIAL = "special"
    BODY_TYPE_CHOICES = [
        (COUNCIL, "City Council"),
        (STANDING_COMMITTEE, "Standing Committee"),
        (COMMUNITY_COUNCIL, "Community Council"),
        (SPECIAL, "Special Committee"),
    ]

    tmmis_meeting_id = models.CharField(max_length=50, unique=True)
    body_type = models.CharField(max_length=20, choices=BODY_TYPE_CHOICES)
    body_name = models.CharField(max_length=200)
    meeting_number = models.PositiveIntegerField(null=True, blank=True)
    meeting_date = models.DateField()

    class Meta:
        indexes = [models.Index(fields=["body_name", "meeting_date"])]
        ordering = ["-meeting_date"]

    def __str__(self):
        return f"{self.body_name} — {self.meeting_date}"


class AgendaItem(SourcedFact):
    """One policy question's full lifecycle, sourced from its consolidated
    "item history" page (secure.toronto.ca/council/agenda-item.do?item=X)
    -- one row per natural item_id (e.g. "2025.EX20.12"), not one row per
    meeting it passed through. tracking_status_text is the City Clerk's
    own plain-English status line and is the single highest-value field
    this feature has -- it's already a written answer to "what happened,"
    not something this site is inferring.
    """

    ADOPTED = "adopted"
    AMENDED = "amended"
    DEFERRED = "deferred"
    NOT_ADOPTED = "not_adopted"
    RECEIVED = "received"
    REFERRED = "referred"
    UNKNOWN = "unknown"
    STATUS_CHOICES = [
        (ADOPTED, "Adopted"),
        (AMENDED, "Adopted with amendments"),
        (DEFERRED, "Deferred"),
        (NOT_ADOPTED, "Not adopted"),
        (RECEIVED, "Received"),
        (REFERRED, "Referred"),
        (UNKNOWN, "Unknown"),
    ]

    item_id = models.CharField(max_length=50, unique=True, db_index=True)
    title = models.CharField(max_length=500)
    primary_meeting = models.ForeignKey(Meeting, on_delete=models.SET_NULL, null=True, blank=True, related_name="agenda_items")
    # Widened past a plausible-looking guess after a real 2026 item's Wards
    # value overflowed 200 chars (some items list many wards by name, not
    # just "All") -- same lesson as apps/lobbying's communication_method.
    consideration_type = models.CharField(max_length=200, blank=True, default="")
    wards = models.CharField(max_length=1000, blank=True, default="")
    origin_text = models.TextField(blank=True, default="")
    summary_text = models.TextField(blank=True, default="")
    decision_text = models.TextField(blank=True, default="")
    tracking_status_text = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=UNKNOWN)
    last_considered_date = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "last_considered_date"])]
        ordering = ["-last_considered_date"]

    def __str__(self):
        return f"{self.item_id} — {self.title}"


class BackgroundDocument(models.Model):
    """A staff report or other PDF attached to an AgendaItem. extracted_text
    is a v2 enrichment (PDF text extraction) -- not populated by the v1
    pilot ingestion, which relies on tracking_status_text/decision_text as
    the source of truth. Kept as its own model now so v2 can backfill
    extracted_text without a schema change.
    """

    item = models.ForeignKey(AgendaItem, on_delete=models.CASCADE, related_name="background_documents")
    title = models.CharField(max_length=500, blank=True, default="")
    pdf_url = models.URLField(max_length=1000)
    extracted_text = models.TextField(blank=True, default="")

    def __str__(self):
        return self.title or self.pdf_url


class NewsCitation(models.Model):
    """A hand-verified news article supporting narrative/causal framing
    (e.g. "following public backlash") that the official record doesn't
    state in those words. Deliberately small and curated -- see
    /methodology -- not bulk-scraped, same discipline as the property-tax
    rate history in apps/budget/taxonomy.py.
    """

    items = models.ManyToManyField(AgendaItem, related_name="news_citations")
    title = models.CharField(max_length=500)
    url = models.URLField(max_length=1000)
    publisher = models.CharField(max_length=200)
    published_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_date"]

    def __str__(self):
        return f"{self.publisher}: {self.title}"
