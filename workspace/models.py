"""
Core Application Models

This module defines the primary data structures for the platform's business logic,
team management, marketplace supply systems, and communications.
"""
import os
import logging
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel

logger = logging.getLogger(__name__)

# ==============================================================================
# SECTION 2: TEAMS SYSTEM
# ==============================================================================

class Team(TimeStampedModel):
    class TeamType(models.TextChoices):
        STARTUP = 'STARTUP', _('Startup Venture')
        BUSINESS = 'BUSINESS', _('SME / Business')
        PROJECT = 'PROJECT', _('Specific Project')
        HACKATHON = 'HACK', _('Hackathon Team')
        LEARNING = 'LEARNING', _('Learning Group')
        NON_PROFIT = 'NON_PROFIT', _('Social Impact')

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('⏳ Pending Admin Review')
        APPROVED = 'APPROVED', _('✅ Active (Public)')
        REJECTED = 'REJECTED', _('❌ Rejected')
        ARCHIVED = 'ARCHIVED', _('📦 Archived')

    # 1. Identity Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Team Name"), max_length=150, unique=True)
    slug = models.SlugField(
        max_length=200,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Auto-generated from name. Must be unique.")
    )

    # 2. Content Fields
    mission = models.TextField(_("Mission Statement"))
    team_type = models.CharField(max_length=20, choices=TeamType.choices, default=TeamType.PROJECT)
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='led_teams',
        null=True,
        blank=True
    )
    roles_needed = models.TextField(_("Roles Needed"), null=True, blank=True)
    telegram_link = models.URLField(_("Telegram Group Link"), blank=True, null=True)

    # 3. Management Fields
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    is_recruiting = models.BooleanField(_("Accepting Members"), default=True)
    admin_feedback = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Team")
        verbose_name_plural = _("Teams")
        ordering =['-created_at', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def get_absolute_url(self):
        """Standard Django practice for linking to objects."""
        return reverse('team_detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        """
        Robust slug generation logic:
        1. Only generates slug if it doesn't exist.
        2. Handles duplicate names by appending a counter.
        3. Handles non-ASCII characters (fallback to UUID snippet).
        """
        if not self.slug:
            # Generate initial slug
            base_slug = slugify(self.name)

            # Fallback for names that slugify to nothing (e.g., only emojis/special chars)
            if not base_slug:
                base_slug = str(self.id)[:8]

            queryset = Team.objects.all()
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)

            final_slug = base_slug
            counter = 1

            # Efficiently check for existing slugs
            while queryset.filter(slug=final_slug).exists():
                final_slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = final_slug

        super().save(*args, **kwargs)


class TeamMembership(TimeStampedModel):
    class Role(models.TextChoices):
        LEADER = 'LEADER', _('👑 Leader')
        MEMBER = 'MEMBER', _('🛠️ Member')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='team_memberships')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        unique_together = ('team', 'user')
        verbose_name = _("Team Membership")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} as {self.get_role_display()} in {self.team}"


class JoinRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('⏳ Pending Leader Review')
        APPROVED = 'APPROVED', _('✅ Accepted')
        REJECTED = 'REJECTED', _('❌ Declined')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='join_requests')
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='team_applications')
    narrative = models.TextField(_("Why do you want to join?"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    class Meta:
        unique_together = ('team', 'applicant')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.applicant} → {self.team} ({self.get_status_display()})"


# ==============================================================================
# SECTION 3: MARKETPLACE SUPPLY
# ==============================================================================

class PreferenceApplication(TimeStampedModel):
    class SeekingType(models.TextChoices):
        JOB = 'JOB', _('Seeking Professional Job')
        INTERNSHIP = 'INTERNSHIP', _('Seeking Internship')
        BOTH = 'BOTH', _('Open to Either')

    class Status(models.TextChoices):
        SUBMITTED = 'SUBMITTED', _('Application Received')
        VETTING = 'VETTING', _('Admin Reviewing Talents')
        HUNTING = 'HUNTING', _('Proactively Finding Matches')
        PLACED = 'PLACED', _('Successfully Placed')
        ARCHIVED = 'ARCHIVED', _('Closed / Not Seeking')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='placement_preferences')
    target_role_title = models.CharField(max_length=150)
    seeking = models.CharField(max_length=15, choices=SeekingType.choices, default=SeekingType.BOTH)
    preferred_location = models.CharField(max_length=255)
    ideal_company_desc = models.TextField()
    value_proposition = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    admin_match_notes = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Preference Application")
        verbose_name_plural = _("Preference Applications")
        ordering = ['-created_at', 'target_role_title']

    def __str__(self):
        return f"{self.user} | Seeking: {self.target_role_title}"


class ConnectionRequest(TimeStampedModel):
    class Status(models.TextChoices):
        APPLIED = 'APPLIED', _('Applied (Pending)')
        REVIEWING = 'REVIEWING', _('Admin Reviewing')
        MATCHING = 'MATCHING', _('Finding Match')
        CONNECTED = 'CONNECTED', _('Introduction Made')
        REJECTED = 'REJECTED', _('Rejected')
        CLOSED = 'CLOSED', _('Closed')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='connection_applications')
    title = models.CharField(max_length=150)
    description = models.TextField()
    target_people_description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED, db_index=True)
    admin_notes = models.TextField(blank=True)
    assigned_connection = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_introductions'
    )

    class Meta:
        verbose_name = _("Connection Request")
        verbose_name_plural = _("Connection Requests")
        ordering = ['-created_at', 'title']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class CompanyMessageToAdmin(TimeStampedModel):
    class Status(models.TextChoices):
        SUBMITTED = 'SUBMITTED', _('Submitted (Pending)')
        REVIEWING = 'REVIEWING', _('Admin Reviewing')
        ACTIONING = 'ACTIONING', _('Action in Progress')
        RESOLVED = 'RESOLVED', _('Resolved')
        CLOSED = 'CLOSED', _('Closed')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    company = models.ForeignKey('profiles.Company', on_delete=models.CASCADE, related_name='admin_messages')
    founder = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='admin_messages')

    # Content
    title = models.CharField(max_length=150)
    description = models.TextField(help_text="The long-form essay of your needs, vision, or challenges.")

    # Admin Tracking
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    admin_notes = models.TextField(blank=True)
    assigned_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_company_messages'
    )

    class Meta:
        verbose_name = _("Message to Admin")
        verbose_name_plural = _("Messages to Admin")
        ordering = ['-created_at', 'title']

    def __str__(self):
        return f"{self.title} - {self.company.name} ({self.get_status_display()})"


# ==============================================================================
# SECTION 4: COMMUNICATIONS / CHAT
# ==============================================================================

class ChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_messages', on_delete=models.CASCADE)

    body = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)  # Indexed for sorting
    is_read = models.BooleanField(default=False)
    # 1. ADDITIVE FIELDS (Safe for live users)
    attachment = models.FileField(upload_to='chat_attachments/%Y/%m/', blank=True, null=True)
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    # 2. SMART PROPERTIES (Helps the template know if it's an image or a PDF)
    @property
    def is_image(self):
        if not self.attachment:
            return False
        ext = os.path.splitext(self.attachment.name)[1].lower()
        return ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']


    @property
    def filename(self):
        if self.attachment:
            return os.path.basename(self.attachment.name)
        return None
    class Meta:
        ordering = ['timestamp']
        indexes =[
            models.Index(fields=['sender', 'receiver']),
        ]

    def __str__(self):
        return f"Message {self.id} from {self.sender} to {self.receiver}"