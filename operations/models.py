import uuid
from typing import Final
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

# ==============================================================================
# EXTERNAL DEPENDENCIES
# ==============================================================================
from core.models import TimeStampedModel


# ==============================================================================
# FILE UPLOAD HANDLERS
# Scalability: Partition files to prevent directory bloating
# ==============================================================================
def evidence_file_path(instance, filename: str) -> str:
    """private/claims/<user_id>/<random>.ext"""
    ext = filename.split('.')[-1]
    return f"private/claims/{instance.user.pk}/{uuid.uuid4().hex[:12]}.{ext}"


def evidence_image_path(instance, filename: str) -> str:
    """public/claims/<user_id>/<random>.ext"""
    ext = filename.split('.')[-1]
    return f"public/claims/{instance.user.pk}/{uuid.uuid4().hex[:12]}.{ext}"


# ==============================================================================
# DOMAIN MODELS
# ==============================================================================

class AchievementClaim(TimeStampedModel):
    """
    Table 23: Proof of Merit.
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('🟡 Pending Review')
        VERIFIED = 'VERIFIED', _('🟢 Verified')
        REJECTED = 'REJECTED', _('🔴 Rejected')
        NEEDS_INFO = 'NEEDS_INFO', _('🔵 Needs More Info')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # DB Index added because we often filter claims by User
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='claims',
        db_index=True
    )

    title = models.CharField(max_length=200)
    description = models.TextField()

    # Optimized paths
    evidence_file = models.FileField(upload_to=evidence_file_path, null=True, blank=True)
    evidence_image = models.ImageField(upload_to=evidence_image_path, null=True, blank=True)
    evidence_link = models.URLField(blank=True)

    # Enum enforced
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True  # Crucial for Admin filtering
    )

    admin_feedback = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Achievement Claim")
        verbose_name_plural = _("Achievement Claims")
        ordering = ['-created_at']


class FamilyUnit(TimeStampedModel):
    """
    Table 24: Micro-Community Shell.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, db_index=True)

    lead_mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='mentored_families'
    )

    telegram_link = models.URLField(max_length=500)

    class Meta:
        verbose_name = _("Family Unit")
        verbose_name_plural = _("Family Units")

    def __str__(self):
        return self.name


class FamilyMembership(TimeStampedModel):
    """
    Table 25: User-Family Link.
    Enforces strict 1-User-1-Family rule via OneToOneField.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    family = models.ForeignKey(
        FamilyUnit,
        on_delete=models.CASCADE,
        related_name='members'
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='family_membership'
    )

    class Meta:
        verbose_name = _("Family Membership")
        # Ensure fast lookups for "Who is in Family X?"
        indexes = [
            models.Index(fields=['family']),
        ]

    def __str__(self):
        return f"{self.user} -> {self.family}"


class AuditLog(models.Model):
    """
    Table 28: Security Blackbox.
    Immutable ledger of all Admin actions.
    OPTIMIZED: High-performance indexing for rapid security filtering.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_actions',
        db_index=True
    )

    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_records'
    )

    action = models.CharField(max_length=200, db_index=True)  # Indexed for filtering

    # PostgreSQL JSONB field (Assuming Postgres backend)
    details = models.JSONField(default=dict, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)  # Indexed for date range queries

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "⚠️ Security Blackbox"
        verbose_name_plural = "⚠️ Security Blackbox"
        # Composite index for common query: "What did Admin X do on Date Y?"
        indexes = [
            models.Index(fields=['admin', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.admin} -> {self.action}"