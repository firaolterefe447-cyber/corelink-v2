import uuid
from typing import Any, List

from django.conf import settings
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
    MinLengthValidator,
)
from django.db import models
from django.db.models import CheckConstraint, Q
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from .utils import (
    SEARCH_OPTIONS,
    COLLAB_CHOICES,
)


class VisionaryProfile(TimeStampedModel):
    """
    Central identity model for the Visionary tier. Bridges authenticated users
    to the platform's mentoring and application systems.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="visionary_profile",
    )

    # --- Identity & Academic Status ---
    slug = models.SlugField(
        _("Profile URL Slug"),
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
    )
    institution = models.CharField(
        _("Institution / School"), max_length=200, db_index=True, null=True, blank=True
    )
    current_title = models.CharField(max_length=100, null=True, blank=True)
    field_of_interest = models.CharField(
        _("Primary Interest"), max_length=100, null=True, blank=True, db_index=True
    )
    location = models.CharField(
        _("Location"), max_length=100, db_index=True, null=True, blank=True
    )

    # --- Narrative & Vision ---
    bio_narrative = models.TextField(_("Long-term Goal"), blank=True)
    headline = models.CharField(
        _("Professional Headline"), max_length=500, null=True, blank=True
    )
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
    last_signal_update = models.DateTimeField(default=timezone.now)
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

    class Meta:
        verbose_name = _("Visionary Profile")
        verbose_name_plural = _("Visionary Profiles")
        ordering = ["-created_at"]
        constraints = [
            CheckConstraint(
                check=Q(admin_rating__gte=0) & Q(admin_rating__lte=5),
                name="visionary_rating_range_check",
            )
        ]

    @classmethod
    def from_db(
        cls, db: str, field_names: List[str], values: List[Any]
    ) -> "VisionaryProfile":
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
        """
        Ensures URL slugs are securely generated and state changes trigger bandwidth updates.
        """
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

        # Slug Generation
        if not self.slug:
            base_name = getattr(
                self.user, "full_name", getattr(self.user, "username", "user")
            )
            base_slug = slugify(base_name)
            slug = base_slug
            counter = 1
            while (
                VisionaryProfile.objects.filter(slug=slug).exclude(pk=self.pk).exists()
            ):
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        super().save(*args, **kwargs)

        # Reset trackers post-save
        self._initial_right_now = self.right_now
        self._initial_current_search = self.current_search
        self._initial_collaboration_status = self.collaboration_status

    def __str__(self) -> str:
        user_display = getattr(
            self.user, "full_name", getattr(self.user, "username", str(self.user.pk))
        )
        return f"Visionary: {user_display}"


class Certification(models.Model):
    """Stores credential proofs and personal growth reflections."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        VisionaryProfile, on_delete=models.CASCADE, related_name="certifications"
    )

    name = models.CharField(
        _("Certificate Name"), max_length=200, null=True, blank=True
    )
    issuing_organization = models.CharField(
        _("Organization"), max_length=200, null=True, blank=True
    )

    learning_reflection = models.TextField(
        _("Learning Reflection"), null=True, blank=True
    )
    key_takeaways = models.CharField(
        _("Key Takeaways"), max_length=500, null=True, blank=True
    )

    certificate_file = models.FileField(
        _("Certificate File"), upload_to="certs/%Y/", null=True, blank=True
    )
    issue_date = models.DateField(_("Date Issued"), null=True, blank=True)
    certificate_link = models.URLField(_("Credential URL"), null=True, blank=True)

    class Meta:
        ordering = ["-issue_date"]
        verbose_name = _("Certification")
        verbose_name_plural = _("Certifications")

    def __str__(self) -> str:
        return self.name or "Untitled Certificate"


class Project(models.Model):
    """Showcase matrix for Visionary practical application of skills."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        VisionaryProfile, on_delete=models.CASCADE, related_name="projects"
    )

    name = models.CharField(_("Project Title"), max_length=200, null=True, blank=True)
    problem = models.TextField(_("Problem Statement"), null=True, blank=True)
    solution = models.TextField(_("My Solution"), null=True, blank=True)
    link = models.URLField(_("Live Link / GitHub"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name or "Untitled Project"


class ProjectImage(models.Model):
    """Gallery mapping for Visionary Projects."""

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="gallery"
    )
    file = models.ImageField(upload_to="projects/")
    caption = models.CharField(max_length=150, blank=True)


class GrowthLog(models.Model):
    """Daily habit and knowledge tracking framework."""

    LOG_TYPES = [
        ("LEARNING", _("Study/Learning")),
        ("WORK", _("Project Work")),
        ("LIFE", _("Personal/Habits")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        VisionaryProfile, on_delete=models.CASCADE, related_name="growth_logs"
    )

    date = models.DateField(auto_now_add=True, db_index=True)
    category = models.CharField(
        max_length=20, choices=LOG_TYPES, default="LEARNING", db_index=True
    )
    title = models.CharField(max_length=200)
    narrative = models.TextField()

    daily_photo = models.ImageField(
        _("Proof of Work"), upload_to="growth_logs/%Y/%m/", null=True, blank=True
    )
    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date"]
        verbose_name = _("Growth Log")
        verbose_name_plural = _("Growth Logs")

    def __str__(self) -> str:
        return f"{self.date} - {self.title}"


class LearningTarget(models.Model):
    """Goal-setting pipeline for future mastery targets."""

    STATUS_CHOICES = [
        ("INTERESTED", "Interested"),
        ("LEARNING", "Learning"),
        ("MASTERED", "Mastered"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        VisionaryProfile, on_delete=models.CASCADE, related_name="learning_targets"
    )

    skill_name = models.CharField(max_length=100)
    learning_motivation = models.TextField(_("The Why"), blank=True)
    progress_bar = models.PositiveIntegerField(
        _("Progress %"),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="INTERESTED", db_index=True
    )

    def __str__(self) -> str:
        return f"{self.skill_name} ({self.progress_bar}%)"


class VisionBlock(models.Model):
    """Manifesto architecture for long-form essays."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        VisionaryProfile, on_delete=models.CASCADE, related_name="vision_blocks"
    )
    title = models.CharField(max_length=100)
    content = models.TextField(_("Essay Content"))
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
