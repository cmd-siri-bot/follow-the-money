"""Trivial DB query to prevent Supabase's free-tier 7-day-inactivity
auto-pause (docs/00-scope.md's hosting decision flagged this risk; not
built until now). Confirmed live 2026-08-05 that direct database
queries count as activity for this purpose, not just REST API calls --
see docs/08-decision-log.md for the sources checked.

Meant to run on a schedule via .github/workflows/supabase-keepalive.yml,
independent of whether the Django app itself is deployed anywhere --
this only needs DATABASE_URL, not a running server.
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone


class Command(BaseCommand):
    help = "Ping Supabase with a trivial query to reset its 7-day inactivity clock."

    def handle(self, *args, **options):
        with connection.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        self.stdout.write(self.style.SUCCESS(f"Supabase pinged OK at {timezone.now().isoformat()}"))
