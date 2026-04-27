import uuid
from typing import Any, List

from django.conf import settings
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
    MinLengthValidator,
)
from django.db import models
from django.db.models import CheckConstraint, Index, Q, UniqueConstraint
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from .utils import (
    MIN_RATING,
    MAX_RATING,
    SEARCH_OPTIONS,
    COLLAB_CHOICES,
    expert_cv_path,
    expert_credential_path,
    portfolio_path,
)


class ExpertProfile(TimeStampedModel):
    """
    Core identity model for Expert Users. Contains bio-narratives, search objectives,
    and availability metrics utilized by the recommendation engine.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="expert_profile",
        verbose_name=_("Identity Link"),
    )

    # --- Metadata & URLs ---
    slug = models.SlugField(
        _("Profile Slug"), unique=True, null=True, blank=True, db_index=True
    )
    location = models.CharField(_("HQ Location"), max_length=100, db_index=True)

    # --- Professional Narrative ---
    bio_narrative = models.TextField(_("Deep Biography"), blank=True)
    years_experience = models.PositiveSmallIntegerField(_("Seniority"), default=1)
    right_now = models.TextField(
        _("Current Focus"),
        max_length=1000,
        validators=[
            MinLengthValidator(
                200,
                message=_(
                    "Your mission details must be at least 200 characters. Share more context to attract the right people!"
                ),
            )
        ],
        null=True,
        blank=True,
    )

    # --- Operational Status ---
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
    last_signal_update = models.DateTimeField(
        default=timezone.now,
        help_text=_("Timestamp of the latest update. Used to calculate signal decay."),
    )

    # --- Assets & Scoring ---
    cv_file = models.FileField(
        _("PDF Artifact"),
        upload_to=expert_cv_path,
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )
    admin_rating = models.PositiveSmallIntegerField(
        _("Competence Score"),
        default=MIN_RATING,
        validators=[MinValueValidator(MIN_RATING), MaxValueValidator(MAX_RATING)],
        db_index=True,
    )
    is_rating_locked = models.BooleanField(
        _("Admin Rating Lock"),
        default=False,
        help_text=_("Check this to stop the AI Oracle from auto-updating this rating."),
    )

    class Meta:
        verbose_name = _("Expert Profile")
        verbose_name_plural = _("Expert Profiles")
        constraints = [
            CheckConstraint(
                check=Q(admin_rating__gte=MIN_RATING) & Q(admin_rating__lte=MAX_RATING),
                name="expert_rating_range_check",
            )
        ]

    @classmethod
    def from_db(
        cls, db: str, field_names: List[str], values: List[Any]
    ) -> "ExpertProfile":
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
        """Determines if the expert is open to immediate collaboration."""
        return self.collaboration_status == "OPEN"

    def __str__(self) -> str:
        return f"Expert: {self.user_id}"


class ExpertHeadline(models.Model):
    """Unlimited Identity Titles mapping for Expert Profiles."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        ExpertProfile, on_delete=models.CASCADE, related_name="headlines"
    )
    title = models.CharField(_("Headline"), max_length=120)
    is_primary = models.BooleanField(default=False, db_index=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-is_primary", "order"]
        constraints = [
            UniqueConstraint(
                fields=["profile"],
                condition=Q(is_primary=True),
                name="unique_primary_headline_per_profile",
            )
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.profile_id})"


class ExpertSkill(models.Model):
    """Tracks verified technical and soft competencies for Experts."""

    class SkillLevel(models.TextChoices):
        JUNIOR = "JUNIOR", _("Junior")
        SENIOR = "SENIOR", _("Senior")
        MASTER = "MASTER", _("Master")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        ExpertProfile, on_delete=models.CASCADE, related_name="skills"
    )
    name = models.CharField(_("Tag"), max_length=100, db_index=True)
    description = models.TextField(_("Context"), blank=True)
    level = models.CharField(max_length=20, choices=SkillLevel.choices)
    admin_status = models.CharField(max_length=20, default="PENDING", db_index=True)

    class Meta:
        verbose_name = _("Expert Skill")
        indexes = [Index(fields=["profile", "admin_status"], name="skill_status_idx")]


class ExpertCredential(TimeStampedModel):
    """Secure vault for academic and professional certifications."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        ExpertProfile, on_delete=models.CASCADE, related_name="credentials"
    )
    institution = models.CharField(max_length=200)
    degree_title = models.CharField(max_length=200)
    year = models.PositiveSmallIntegerField()
    verification_file = models.FileField(upload_to=expert_credential_path)

    # New field for personal reflection/description
    personal_reflection = models.TextField(
        blank=True,
        null=True,
        help_text="A personal reflection or description of what you learned and achieved with this credential.",
    )

    admin_status = models.CharField(max_length=20, default="PENDING", db_index=True)

    def __str__(self):
        return f"{self.degree_title} from {self.institution}"


class ExpertProject(models.Model):
    """Portfolio narratives outlining the Expert's project history."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        ExpertProfile, on_delete=models.CASCADE, related_name="projects"
    )
    title = models.CharField(max_length=200)
    client_name = models.CharField(max_length=200, blank=True)
    role = models.CharField(max_length=100)
    description = models.TextField(_("Narrative Description"))
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]


class ProjectGalleryImage(models.Model):
    """Visual gallery assets linked to an ExpertProject."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        ExpertProject, on_delete=models.CASCADE, related_name="gallery"
    )
    image = models.ImageField(upload_to=portfolio_path)
    caption = models.CharField(max_length=200, blank=True)


class ExpertExperience(models.Model):
    """Structured career timeline mapped to specific roles and companies."""

    class LocType(models.TextChoices):
        REMOTE = "REMOTE", _("Remote")
        ON_SITE = "ON_SITE", _("On-Site")
        HYBRID = "HYBRID", _("Hybrid")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        ExpertProfile, on_delete=models.CASCADE, related_name="experiences"
    )
    company_name = models.CharField(max_length=200)
    role_title = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    location_type = models.CharField(max_length=50, choices=LocType.choices)
    description = models.TextField(blank=True)


class JobPreference(models.Model):
    """Dynamic preference engine utilized by HR matching algorithms."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expert = models.ForeignKey(
        ExpertProfile, on_delete=models.CASCADE, related_name="job_preferences"
    )
    role_title = models.CharField(max_length=100)
    work_arrangement = models.CharField(max_length=50)
    commitment_type = models.CharField(max_length=50)
    description = models.TextField(_("Preference Narrative"))
    is_active = models.BooleanField(default=True, db_index=True)


class ExpertThought(TimeStampedModel):
    """Markdown-supported thought leadership publishing block."""

    class Visibility(models.TextChoices):
        PUBLIC = "PUBLIC", "Public"
        PRIVATE = "PRIVATE", "Private"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        ExpertProfile, on_delete=models.CASCADE, related_name="thoughts"
    )
    title = models.CharField(max_length=200)
    content = models.TextField(_("Markdown Body"))
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
        db_index=True,
    )
