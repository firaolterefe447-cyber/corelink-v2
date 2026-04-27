import uuid
from typing import Any, Final, List, Tuple

from django.utils.translation import gettext_lazy as _

# ==============================================================================
# DOMAIN CONSTANTS
# ==============================================================================
MIN_RATING: Final[int] = 0
MAX_RATING: Final[int] = 5
MIN_YEAR: Final[int] = 1900
MAX_YEAR: Final[int] = 2100

SEARCH_OPTIONS: Final[List[Tuple[str, str]]] = [
    ("INTERN", _("Looking for an Internship")),
    ("FUNDING", _("Looking for Funding")),
    ("STARTUP", _("Looking for a Startup Team")),
    ("PROJECT", _("Looking for a Project to join")),
    ("MINDSET", _("Looking to meet people with the same mindset")),
    ("LEARNING", _("Just focusing on Studying")),
    ("FULL_TIME", _("Looking for a Full-time Job")),
    ("PART_TIME", _("Looking for a Part-time Job")),
]

COLLAB_CHOICES: Final[List[Tuple[str, str]]] = [
    ("OPEN", _("Open to Collaborate")),
    ("BUSY", _(" Deep Work (Slow Response)")),
    ("CLOSED", _("Not Accepting Requests")),
]


# ==============================================================================
# FILE UPLOAD HANDLERS
# Partitioned by PK to prevent filesystem exhaustion on large buckets
# ==============================================================================
def expert_cv_path(instance: Any, filename: str) -> str:
    ext = filename.split(".")[-1]
    return f"public/resumes/{instance.pk}/{uuid.uuid4().hex[:12]}.{ext}"


def expert_credential_path(instance: Any, filename: str) -> str:
    ext = filename.split(".")[-1]
    return f"private/docs/{instance.profile.pk}/{uuid.uuid4().hex[:12]}.{ext}"


def portfolio_path(instance: Any, filename: str) -> str:
    ext = filename.split(".")[-1]
    return f"public/portfolio/{uuid.uuid4().hex[:12]}.{ext}"


def company_logo_path(instance: Any, filename: str) -> str:
    return f"companies/{instance.id}/logo/{filename}"


def company_cover_path(instance: Any, filename: str) -> str:
    return f"companies/{instance.id}/cover/{filename}"


def news_cover_path(instance: Any, filename: str) -> str:
    return f"companies/{instance.company.id}/news/covers/{filename}"


def news_gallery_path(instance: Any, filename: str) -> str:
    return f"companies/{instance.news.company.id}/news/gallery/{filename}"


# ==============================================================================
# LEGACY MIGRATION STUBS (DO NOT DELETE)
# Required to prevent historical Django migrations from crashing.
# ==============================================================================
def founder_cover_path(instance: Any, filename: str) -> str:
    return f"legacy/covers/{filename}"


def founder_logo_path(instance: Any, filename: str) -> str:
    return f"legacy/logos/{filename}"


def service_gallery_path(instance: Any, filename: str) -> str:
    return f"legacy/services/{filename}"
