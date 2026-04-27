import logging
import uuid
from typing import Any

from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from .user import CustomUser

logger = logging.getLogger(__name__)


class IDSequence(models.Model):
    prefix = models.CharField(
        _("Role Prefix"),
        max_length=10,
        primary_key=True,
        help_text=_("Role identifier (e.g., EXP, VIS, FND)"),
    )
    year = models.IntegerField(
        _("Year Code"),
        help_text=_("Calendar year for sequence grouping"),
    )
    last_number = models.IntegerField(
        _("Last Sequence Number"),
        default=0,
        help_text=_("Last assigned sequence number"),
    )

    class Meta:
        verbose_name = _("ID Sequence Counter")
        verbose_name_plural = _("ID Sequence Counters")
        unique_together = ("prefix", "year")
        indexes = [
            models.Index(fields=["prefix", "year"]),
        ]

    def __str__(self) -> str:
        return f"{self.prefix}-{self.year}: {self.last_number}"

    def get_next_id(self) -> str:
        with transaction.atomic():
            sequence = IDSequence.objects.select_for_update().get(
                prefix=self.prefix,
                year=self.year,
            )
            sequence.last_number += 1
            sequence.save()

            return f"{self.prefix}-{self.year}-{sequence.last_number:03d}"


def application_cv_path(instance: Any, filename: str) -> str:
    ext = filename.split(".")[-1]
    user_id = instance.user.id if instance.user else "unassigned"
    return f"private/applications/{user_id}/{uuid.uuid4().hex[:8]}.{ext}"


class ApplicationRequest(TimeStampedModel):
    class RoleType(models.TextChoices):
        EXPERT = "EXPERT", _("Expert")
        VISIONARY = "VISIONARY", _("Visionary")
        FOUNDER = "FOUNDER", _("Founder")

    class Status(models.TextChoices):
        PENDING = "PENDING", _("🟡 Pending Review")
        APPROVED = "APPROVED", _("🟢 Approved")
        REJECTED = "REJECTED", _("🔴 Rejected")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="application_requests",
        help_text=_("User requesting role upgrade"),
    )
    role_type = models.CharField(
        max_length=20,
        choices=RoleType.choices,
        db_index=True,
        help_text=_("Target role being applied for"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text=_("Current application status"),
    )
    cv_file = models.FileField(
        upload_to=application_cv_path,
        null=True,
        blank=True,
        help_text=_("Supporting CV or document"),
    )
    submission_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional application metadata"),
    )
    admin_notes = models.TextField(
        blank=True,
        help_text=_("Admin review notes and feedback"),
    )

    class Meta:
        verbose_name = "Member Application"
        verbose_name_plural = "Member Applications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "role_type"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.role_type}: {self.user.full_name}"

    def approve(self) -> None:
        if self.status != self.Status.PENDING:
            raise ValueError("Only pending applications can be approved")

        self.user.role = self.role_type
        self.user.save(update_fields=["role"])
        self.status = self.Status.APPROVED
        self.save(update_fields=["status"])

        logger.info(f"User {self.user.id} role upgraded to {self.role_type}")


class CommunityContributor(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(
        max_length=150,
        help_text=_("Volunteer's complete name"),
    )
    email = models.EmailField(
        _("Email Address"),
        help_text=_("Primary email for communication"),
        null=True,
        blank=True,
    )
    telegram_username = models.CharField(
        max_length=100,
        help_text=_("@username for Telegram contact"),
    )
    contribution_area = models.CharField(
        max_length=200,
        help_text=_("Area of interest/expertise"),
    )
    message = models.TextField(
        verbose_name="Why CoreLink?",
        help_text=_("Motivation for joining the community"),
    )
    is_contacted = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Whether the volunteer has been contacted"),
    )

    class Meta:
        verbose_name = "Community Volunteer"
        verbose_name_plural = "Community Volunteers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_contacted", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Volunteer: {self.full_name}"

    def mark_contacted(self) -> None:
        self.is_contacted = True
        self.save(update_fields=["is_contacted"])
