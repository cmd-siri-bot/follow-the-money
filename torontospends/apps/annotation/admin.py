from django.contrib import admin
from django.utils import timezone

from .models import Annotation, Correction


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = (
        "flag_type",
        "content_type",
        "object_id",
        "confidence_score",
        "status",
        "reviewer",
        "reviewed_at",
        "created_at",
    )
    list_filter = ("status", "flag_type", "content_type")
    search_fields = ("description", "reviewer_note")
    readonly_fields = ("content_type", "object_id", "flag_type", "confidence_score", "description", "created_at")
    actions = ["approve_selected", "reject_selected"]

    @admin.action(description="Approve selected flags")
    def approve_selected(self, request, queryset):
        updated = queryset.update(status=Annotation.APPROVED, reviewer=request.user, reviewed_at=timezone.now())
        self.message_user(request, f"{updated} annotation(s) approved.")

    @admin.action(description="Reject selected flags")
    def reject_selected(self, request, queryset):
        updated = queryset.update(status=Annotation.REJECTED, reviewer=request.user, reviewed_at=timezone.now())
        self.message_user(request, f"{updated} annotation(s) rejected.")


@admin.register(Correction)
class CorrectionAdmin(admin.ModelAdmin):
    list_display = ("title", "dataset", "reported_at", "resolved_at", "published")
    list_filter = ("published", "dataset")
    search_fields = ("title", "description")
