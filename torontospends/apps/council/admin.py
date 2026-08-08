from django.contrib import admin

from .models import AgendaItem, BackgroundDocument, Meeting, NewsCitation


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ("body_name", "meeting_date", "tmmis_meeting_id", "body_type")
    list_filter = ("body_type",)
    search_fields = ("body_name", "tmmis_meeting_id")


class BackgroundDocumentInline(admin.TabularInline):
    model = BackgroundDocument
    extra = 0


@admin.register(AgendaItem)
class AgendaItemAdmin(admin.ModelAdmin):
    list_display = ("item_id", "title", "status", "last_considered_date")
    list_filter = ("status",)
    search_fields = ("item_id", "title", "summary_text", "decision_text")
    inlines = [BackgroundDocumentInline]
    autocomplete_fields = ("primary_meeting",)


@admin.register(NewsCitation)
class NewsCitationAdmin(admin.ModelAdmin):
    list_display = ("publisher", "title", "published_date")
    search_fields = ("title", "publisher")
    filter_horizontal = ("items",)
