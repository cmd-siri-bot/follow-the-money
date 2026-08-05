"""Re-exports common.normalize_names -- moved there 2026-08-05 so
TorontoSpends can share this logic. Kept here so every existing script's
`from normalize_names import ...` (via each script's own sys.path.insert
of this directory) keeps working unchanged.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common.normalize_names import (  # noqa: E402,F401
    normalize_whitespace,
    normalize_postal,
    strip_accents_for_matching,
    split_last_first,
    normalize_name,
    org_key,
)
