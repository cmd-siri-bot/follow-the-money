from django.contrib import admin

from .models import Entity, RawRecord


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ("display_name", "entity_type", "match_key", "updated_at")
    list_filter = ("entity_type",)
    search_fields = ("display_name", "match_key")


@admin.register(RawRecord)
class RawRecordAdmin(admin.ModelAdmin):
    list_display = ("source_system", "retrieved_at", "processed", "created_at")
    list_filter = ("source_system", "processed")
    readonly_fields = ("payload",)
