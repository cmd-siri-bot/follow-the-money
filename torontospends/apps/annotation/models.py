from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Annotation(models.Model):
    """The human-review-queue pattern, generalized to any model in the
    system via a GenericForeignKey. Mirrors what Follow the Money already
    does by hand in its kg_adjudicate_*.py worksheets
    (reviewer_verdict/reviewer_note columns, sign-off required before a
    named entity's data goes further) -- here it's a Django admin queue
    instead of a CSV, per ADR-007's reasoning for keeping this stack.

    Every statistical flag or AI-suggested entity merge must go through
    this queue before it affects anything public-facing. Per this
    project's editorial standard: confidence_score is required whenever
    a flag_type represents a classification, never a bare true/false.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = [(PENDING, "Pending"), (APPROVED, "Approved"), (REJECTED, "Rejected")]

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    flag_type = models.CharField(max_length=100)
    confidence_score = models.FloatField(null=True, blank=True)
    description = models.TextField(blank=True, default="")

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="annotations_reviewed"
    )
    reviewer_note = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["status", "flag_type"]),
        ]

    def __str__(self):
        return f"{self.flag_type} on {self.content_object} [{self.status}]"


class Correction(models.Model):
    """A publicly-logged correction, per /methodology's stated correction
    policy: any factual error reported and confirmed goes here, dated and
    described, rather than being silently edited away. Public-facing --
    only published=True rows render on /corrections, so a correction can
    be drafted in the admin before it goes live.
    """

    title = models.CharField(max_length=300)
    description = models.TextField()
    dataset = models.CharField(max_length=100, blank=True, default="")  # e.g. "budget", "lobbying", "grants" -- free text, not enforced
    reported_at = models.DateField()
    resolved_at = models.DateField(null=True, blank=True)
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-reported_at"]

    def __str__(self):
        return self.title
