"""
CoreLink Foundation Models

Foundational models providing base functionality for the entire CoreLink platform.
Includes abstract base classes, media management, and system-wide utilities.
"""

# System Imports & Dependencies
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

# Abstract Base Classes

class TimeStampedModel(models.Model):
    """Abstract base class providing automatic timestamp tracking."""
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp when the record was created")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_("Timestamp when the record was last updated")
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]


