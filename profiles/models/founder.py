from typing import Any, List

from django.conf import settings
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    MinLengthValidator,
)
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from .utils import (
    SEARCH_OPTIONS,
    COLLAB_CHOICES,
)


class FounderProfile(TimeStampedModel):
    """
    Personal identity abstraction for users operating a Company.
    NOTE: The legacy 'Name Section' data preservation fields have been strictly removed.
    """

    ##"""TEMPE"""
    company_name = models.CharField(max_length=200, null=True, blank=True)
    sector = models.CharField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    mission_stmt = models.TextField(null=True, blank=True)
    #####TEMPRO
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="founder_profile",
    )
    slug = models.SlugField(
        _("Profile Slug"), unique=True, null=True, blank=True, db_index=True
    )

    # --- Operational Status ---
    right_now = models.TextField(
        _("Current Focus"),
        max_length=1000,
        validators=[
            MinLengthValidator(
                20,
                message=_(
                    "Your mission details must be at least 200 characters. Share more context to attract the right people!"
                ),
            )
        ],
        null=True,
        blank=True,
    )
    current_search = models.CharField(
        _("Current Objective"),
        max_length=20,
        choices=SEARCH_OPTIONS,
        default="LEARNING",
        null=True,
        blank=True,
        db_index=True,
    )
    collaboration_status = models.CharField(
        _("Availability"), max_length=20, choices=COLLAB_CHOICES, default="OPEN"
    )
    # Replace the existing last_signal_update field with this:
    last_signal_update = models.DateTimeField(
        default=timezone.now,
        help_text=_("Timestamp of the latest update. Used to calculate signal decay."),
    )
    admin_rating = models.PositiveSmallIntegerField(
        _("Admin Rating"),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        db_index=True,
    )
    is_rating_locked = models.BooleanField(
        _("Admin Rating Lock"),
        default=False,
        help_text=_("Check this to stop the AI Oracle from auto-updating this rating."),
    )

    @classmethod
    def from_db(
        cls, db: str, field_names: List[str], values: List[Any]
    ) -> "FounderProfile":
        """Overrides model instantiation to accurately capture initial states for signal decay calculations."""
        instance = super().from_db(db, field_names, values)
        if "right_now" in field_names:
            instance._initial_right_now = instance.right_now
        if "current_search" in field_names:
            instance._initial_current_search = instance.current_search
        if "collaboration_status" in field_names:
            instance._initial_collaboration_status = instance.collaboration_status
        return instance

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Ensures state changes trigger bandwidth updates."""
        if self.pk:
            changed = False
            if hasattr(self, "_initial_right_now") and self.right_now != getattr(
                self, "_initial_right_now"
            ):
                changed = True
            if hasattr(
                self, "_initial_current_search"
            ) and self.current_search != getattr(self, "_initial_current_search"):
                changed = True
            if hasattr(
                self, "_initial_collaboration_status"
            ) and self.collaboration_status != getattr(
                self, "_initial_collaboration_status"
            ):
                changed = True

            if changed:
                self.last_signal_update = timezone.now()

        super().save(*args, **kwargs)

        # Reset trackers post-save
        self._initial_right_now = self.right_now
        self._initial_current_search = self.current_search
        self._initial_collaboration_status = self.collaboration_status

    @property
    def is_available(self) -> bool:
        """Determines if the founder is open to new collaborations."""
        return self.collaboration_status == "OPEN"

    def __str__(self) -> str:
        # Resolves previous bug where __str__ broke the class structure
        return f"Founder Profile: {getattr(self.user, 'full_name', self.user.id)}"
