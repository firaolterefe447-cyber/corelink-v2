"""
CoreLink Unified Portfolio System

A fluid professional identity system that replaces rigid profile boxes with a unified
profile where users attach modular blocks (Skills, Projects, Content, Credentials)
that evolve with their career.
"""

# System Imports & Dependencies
import uuid
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Any, List

from django.conf import settings
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator, MinLengthValidator
from django.db import models, transaction
from django.db.models import F
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from core.services import optimize_standard_image
from .utils import SEARCH_OPTIONS, COLLAB_CHOICES

logger = logging.getLogger(__name__)


# Media & Storage Allocation Functions

def profile_cv_path(instance: Any, filename: str) -> str:
    ext = filename.split('.')[-1]
    return f"portfolio/resumes/{instance.pk}/{uuid.uuid4().hex[:12]}.{ext}"

def credential_path(instance: Any, filename: str) -> str:
    ext = filename.split('.')[-1]
    return f"portfolio/credentials/{instance.profile.pk}/{uuid.uuid4().hex[:12]}.{ext}"

def project_image_path(instance: Any, filename: str) -> str:
    ext = filename.split('.')[-1]
    return f"portfolio/projects/{uuid.uuid4().hex[:12]}.{ext}"

def content_media_path(instance: Any, filename: str) -> str:
    ext = filename.split('.')[-1]
    return f"portfolio/content/{instance.profile.pk}/{uuid.uuid4().hex[:12]}.{ext}"

def right_now_media_path(instance: Any, filename: str) -> str:
    ext = filename.split('.')[-1]
    return f"portfolio/right_now/{instance.post.profile.pk}/{uuid.uuid4().hex[:12]}.{ext}"

def service_gallery_path(instance: Any, filename: str) -> str:
    ext = filename.split('.')[-1]
    return f"portfolio/services/{instance.service.profile.pk}/{uuid.uuid4().hex[:12]}.{ext}"


# Core Identity Layer

class UserProfile(TimeStampedModel):
    """The Core Identity - replaces both ExpertProfile and VisionaryProfile."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='portfolio'
    )
    slug = models.SlugField(_("Profile URL Slug"), max_length=255, unique=True, blank=True, db_index=True)

    # Legacy Data Preservation
    location = models.CharField(_("Location"), max_length=100, blank=True, null=True)
    institution = models.CharField(_("Institution / School"), max_length=200, blank=True, null=True)
    field_of_interest = models.CharField(_("Primary Interest"), max_length=100, blank=True, null=True)
    years_experience = models.PositiveSmallIntegerField(_("Years of Experience"), default=0)

    # Professional Narrative
    bio_narrative = models.TextField(_("Deep Biography / Long-term Goal"), blank=True)

    # Legacy Fields Preserved for Migration
    current_mission = models.TextField(
        _("Current Focus (Right Now)"),
        max_length=1000,
        validators=[MinLengthValidator(20)],
        blank=True, null=True,
        help_text=_("What are you building or learning this exact month? (Migrated from 'right_now')")
    )

    # Real-Time Networking Intent
    current_search = models.CharField(
        _("Current Objective"),
        max_length=20, choices=SEARCH_OPTIONS, default='LEARNING', db_index=True
    )
    collaboration_status = models.CharField(
        _("Availability"), max_length=20, choices=COLLAB_CHOICES, default='OPEN', db_index=True
    )

    # Scoring & Algorithms
    admin_rating = models.PositiveSmallIntegerField(
        _("Platform Rating"), default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    oracle_score = models.PositiveSmallIntegerField(
        _("Raw AI Score"), default=0, db_index=True,
        help_text="The exact 1-100 score calculated by the Oracle. Used for granular feed sorting."
    )
    is_rating_locked = models.BooleanField(default=False)
    last_signal_update = models.DateTimeField(default=timezone.now, db_index=True)

    # Profile Verification
    profile_verified = models.BooleanField(
        _("Profile Verified"), default=False,
        help_text="Indicates if the user has completed a complete profile and is verified by the platform"
    )

    # Assets
    cv_file = models.FileField(
        _("Resume / CV PDF"), upload_to=profile_cv_path, null=True, blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )

    class Meta:
        verbose_name = _("Unified Profile")
        verbose_name_plural = _("Unified Profiles")
        indexes = [
            models.Index(fields=['current_search', '-last_signal_update']),
            models.Index(fields=['collaboration_status']),
        ]

    @classmethod
    def from_db(cls, db: str, field_names: List[str], values: List[Any]) -> 'UserProfile':
        """Overrides model instantiation to accurately capture initial states (Zero DB Hits)."""
        instance = super().from_db(db, field_names, values)
        if 'current_mission' in field_names:
            instance._initial_current_mission = instance.current_mission
        if 'current_search' in field_names:
            instance._initial_current_search = instance.current_search
        return instance

    def save(self, *args, **kwargs):
        """Auto-generates slug and updates signal decay based on intent changes."""
        # Update Signal Decay (Only if values actually changed)
        if self.pk:
            changed = False
            if hasattr(self, '_initial_current_mission') and self.current_mission != getattr(self, '_initial_current_mission'):
                changed = True
            if hasattr(self, '_initial_current_search') and self.current_search != getattr(self, '_initial_current_search'):
                changed = True

            if changed:
                self.last_signal_update = timezone.now()

        # Slug Generation
        if not self.slug:
            base_name = getattr(self.user, 'full_name', getattr(self.user, 'phone_number', 'user'))
            base_slug = slugify(base_name) or 'user'
            slug = base_slug
            counter = 1
            while UserProfile.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        super().save(*args, **kwargs)

        # Reset trackers post-save
        self._initial_current_mission = self.current_mission
        self._initial_current_search = self.current_search

    def __str__(self):
        user_display = getattr(self.user, 'full_name', getattr(self.user, 'phone_number', str(self.pk)))
        return f"Portfolio: {user_display}"


class ProfileHeadline(models.Model):
    """Allows users to have multiple identities (e.g., 'Senior Dev' & 'Angel Investor')."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='headlines')
    title = models.CharField(_("Headline"), max_length=120)
    is_primary = models.BooleanField(default=False, db_index=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-is_primary', 'order']


# Foundation Layer (Resume & Verification Blocks)

class WorkExperience(models.Model):
    """Standard CV timeline mapping roles & companies."""
    class LocType(models.TextChoices):
        REMOTE = 'REMOTE', _('Remote')
        ON_SITE = 'ON_SITE', _('On-Site')
        HYBRID = 'HYBRID', _('Hybrid')

    class EmploymentType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', _('Full-time')
        PART_TIME = 'PART_TIME', _('Part-time')
        CONTRACT = 'CONTRACT', _('Contract')
        INTERNSHIP = 'INTERNSHIP', _('Internship')
        FREELANCE = 'FREELANCE', _('Freelance')
        VOLUNTEER = 'VOLUNTEER', _('Volunteer')
        APPRENTICESHIP = 'APPRENTICESHIP', _('Apprenticeship')
        OTHER = 'OTHER', _('Other')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='experiences')

    company_name = models.CharField(max_length=200)
    role_title = models.CharField(max_length=200)
    location_type = models.CharField(max_length=50, choices=LocType.choices, default=LocType.ON_SITE)
    employment_type = models.CharField(
        max_length=50,
        choices=EmploymentType.choices,
        blank=True,
        null=True
    )

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    date_display = models.CharField(_("Custom Date Display"), max_length=100, blank=True, help_text=_("Enter date in any format (e.g., '2023-2024', 'Summer 2023', '2023 - Present'). This will be displayed on your portfolio."))
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)


class Credential(TimeStampedModel):
    """A unified vault for all verifiable education and certifications."""
    class CredentialType(models.TextChoices):
        DEGREE = 'DEGREE', _('University Degree')
        CERTIFICATE = 'CERTIFICATE', _('Professional Certificate')
        COURSE = 'COURSE', _('Online Course / Bootcamp')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='credentials')

    credential_type = models.CharField(max_length=20, choices=CredentialType.choices, default=CredentialType.CERTIFICATE)
    title = models.CharField(_("Degree / Certificate Name"), max_length=200)
    issuer = models.CharField(_("Issuing Organization"), max_length=200)

    reflection = models.TextField(_("Personal Reflection"), blank=True, null=True)
    key_takeaways = models.CharField(max_length=500, blank=True, null=True)

    issue_date = models.DateField(null=True, blank=True)
    file_upload = models.FileField(upload_to=credential_path, null=True, blank=True)
    url_link = models.URLField(_("Verification URL"), max_length=500, blank=True, null=True)

    is_admin_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ['-issue_date']


class Skill(models.Model):
    """A skill flows from INTERESTED -> LEARNING -> MASTERED natively."""
    class SkillStatus(models.TextChoices):
        INTERESTED = 'INTERESTED', _('Interested in learning')
        LEARNING = 'LEARNING', _('Actively Learning')
        MASTERED = 'MASTERED', _('Mastered / Using professionally')

    class Proficiency(models.TextChoices):
        JUNIOR = 'JUNIOR', _('Junior')
        SENIOR = 'SENIOR', _('Senior')
        MASTER = 'MASTER', _('Master')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='skills')

    name = models.CharField(_("Skill Name"), max_length=100, db_index=True)
    context = models.TextField(_("Context / Motivation"), blank=True)
    status = models.CharField(max_length=20, choices=SkillStatus.choices, default=SkillStatus.LEARNING)

    progress_bar = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(100)])
    proficiency_level = models.CharField(max_length=20, choices=Proficiency.choices, blank=True, null=True)
    admin_status = models.CharField(max_length=20, default='PENDING')

    class Meta:
        ordering = ['-status', 'name']


class Language(models.Model):
    """User language proficiency with Ethiopian languages and custom input support."""
    class ProficiencyLevel(models.TextChoices):
        NATIVE = 'NATIVE', _('Native')
        FLUENT = 'FLUENT', _('Fluent / Professional')
        INTERMEDIATE = 'INTERMEDIATE', _('Intermediate / Conversational')
        BASIC = 'BASIC', _('Basic / Beginner')

    # Ethiopian Languages (ISO 639-1 codes where available)
    ETHIOPIAN_LANGUAGES = [
        ('am', _('Amharic')),
        ('om', _('Afan Oromo')),
        ('ti', _('Tigrinya')),
        ('so', _('Somali')),
        ('aa', _('Afar')),
        ('sid', _('Sidamigna')),
        ('wal', _('Wolayigna')),
        ('gur', _('Gurage (General)')),
    ]

    # Common International Languages
    INTERNATIONAL_LANGUAGES = [
        ('en', _('English')),
        ('ar', _('Arabic')),
        ('fr', _('French')),
        ('es', _('Spanish')),
        ('de', _('German')),
        ('zh', _('Chinese')),
        ('ja', _('Japanese')),
        ('pt', _('Portuguese')),
        ('ru', _('Russian')),
        ('it', _('Italian')),
        ('hi', _('Hindi')),
        ('ko', _('Korean')),
        ('tr', _('Turkish')),
        ('fa', _('Persian')),
        ('sw', _('Swahili')),
    ]

    # Combined choices with custom option
    LANGUAGE_CHOICES = ETHIOPIAN_LANGUAGES + INTERNATIONAL_LANGUAGES + [('OTHER', _('Other (Custom)'))]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='languages')

    # Standard language code (ISO 639-1)
    language_code = models.CharField(
        _("Language Code"),
        max_length=10,
        choices=LANGUAGE_CHOICES,
        db_index=True
    )

    # Custom language name (if 'OTHER' is selected)
    custom_language_name = models.CharField(
        _("Custom Language Name"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Required if 'Other' is selected")
    )

    proficiency = models.CharField(
        _("Proficiency Level"),
        max_length=20,
        choices=ProficiencyLevel.choices,
        default=ProficiencyLevel.INTERMEDIATE,
        db_index=True
    )

    is_primary = models.BooleanField(
        _("Primary Language"),
        default=False,
        help_text=_("Mark as your primary/native language")
    )

    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-is_primary', 'order', 'language_code']
        verbose_name = _("Language")
        verbose_name_plural = _("Languages")

    def clean(self):
        """Validate that custom_language_name is provided when OTHER is selected."""
        from django.core.exceptions import ValidationError
        if self.language_code == 'OTHER' and not self.custom_language_name:
            raise ValidationError(_("Custom language name is required when 'Other' is selected."))

    def get_language_display(self):
        """Get the display name for the language."""
        if self.language_code == 'OTHER':
            return self.custom_language_name or _('Other')
        return dict(self.LANGUAGE_CHOICES).get(self.language_code, self.language_code)

    def __str__(self):
        lang_name = self.get_language_display()
        return f"{lang_name} - {self.get_proficiency_display()}"


# Proof of Work & Expression Layer

class PortfolioProject(TimeStampedModel):
    """The ultimate proof-of-work display for professional portfolios."""

    class Category(models.TextChoices):
        SOFTWARE_DATA = 'SOFTWARE_DATA', _('Software, AI & Data Science')
        HARDWARE_ROBOTICS = 'HARDWARE_ROBOTICS', _('Hardware, Engineering & Robotics')
        MEDICAL_CLINICAL = 'MEDICAL_CLINICAL', _('Medicine, Healthcare & Biotech')
        LEGAL_POLICY = 'LEGAL_POLICY', _('Law, Public Policy & Gov')
        SCIENCE_RESEARCH = 'SCIENCE_RESEARCH', _('Academic Science & Lab Research')
        DESIGN_UX = 'DESIGN_UX', _('UI/UX, Product & Graphic Design')
        ARCHITECTURE_CIVIL = 'ARCHITECTURE_CIVIL', _('Architecture & Civil Engineering')
        BUSINESS_FINANCE = 'BUSINESS_FINANCE', _('Business, Finance & Startups')
        MARKETING_MEDIA = 'MARKETING_MEDIA', _('Marketing, Journalism & Media')
        ARTS_CREATIVE = 'ARTS_CREATIVE', _('Film, Music, Photography & Fine Arts')
        EDUCATION_TRAINING = 'EDUCATION_TRAINING', _('Education, Curriculum & Training')
        OPERATIONS_TRADES = 'OPERATIONS_TRADES', _('Operations, Culinary & Skilled Trades')
        OTHER = 'OTHER', _('Interdisciplinary / Niche')

    class ProjectContext(models.TextChoices):
        PRACTICE = 'PRACTICE', _('Learning / Bootcamp Project')
        REAL_WORLD = 'REAL_WORLD', _('Real-world / Client Project')
        STARTUP = 'STARTUP', _('Startup / Own Company')
        PUBLISHED = 'PUBLISHED', _('Published / Peer-Reviewed')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='projects')

    # --- 1. NEW FUTURIST FIELDS (Default safely removed here) ---
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        db_index=True,
        blank=True,
        null=True,
        help_text=_("The core industry of this project. Auto-detected if not provided.")
    )
    meta_attributes = models.JSONField(
        _("Domain Specific Data"), default=dict, blank=True,
        help_text=_(
            "Stores infinite profession-specific inputs natively (e.g., {'jurisdiction': 'NY'} or {'tech_stack': ['React']})")
    )

    # Legacy Data (Strictly Preserved)
    title = models.CharField(max_length=200)
    context = models.CharField(max_length=20, choices=ProjectContext.choices, default=ProjectContext.PRACTICE)
    role = models.CharField(max_length=100, blank=True)
    client_name = models.CharField(max_length=200, blank=True)
    problem_statement = models.TextField(blank=True, null=True)
    solution_narrative = models.TextField(blank=True, null=True)
    main_description = models.TextField(_("Main Description"), blank=True)
    link = models.URLField(_("Live Link / GitHub"), max_length=500, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"


class ProjectGallery(models.Model):
    """Upgraded to a Universal Asset Vault (Accepts Images, PDFs, and Embeds)."""

    class AssetType(models.TextChoices):
        IMAGE = 'IMAGE', _('Visual / Screenshot')
        DOCUMENT = 'DOCUMENT', _('PDF Document / Research Paper / Case File')
        EMBED = 'EMBED', _('External Embed (Figma, YouTube, Spotify)')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(PortfolioProject, on_delete=models.CASCADE, related_name='gallery')

    # New Asset Fields
    asset_type = models.CharField(max_length=20, choices=AssetType.choices, default=AssetType.IMAGE)
    document_file = models.FileField(
        upload_to=project_image_path, blank=True, null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    external_url = models.URLField(max_length=500, blank=True, null=True)

    # Legacy Fields (Preserved)
    image = models.ImageField(upload_to=project_image_path, blank=True, null=True)
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Asset for {self.project.title}"


class Service(TimeStampedModel):
    """Professional services offered by users - distinct from company services."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='services')

    title = models.CharField(_("Service Title"), max_length=200, db_index=True)
    description = models.TextField(_("Service Description"), help_text=_("Explain your service in detail"))

    is_active = models.BooleanField(default=True, db_index=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = _("Service")
        verbose_name_plural = _("Services")

    def __str__(self):
        return f"{self.title} ({self.profile.user.full_name if self.profile.user else 'No User'})"


class ServiceGallery(models.Model):
    """Visual gallery for user services to showcase their work."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='gallery')

    image = models.ImageField(upload_to=service_gallery_path)
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name = _("Service Gallery Image")
        verbose_name_plural = _("Service Gallery Images")

    def __str__(self):
        return f"Image for {self.service.title}"


class ContentPost(TimeStampedModel):
    """The unified publishing block adapting to Logs, Essays, and Vision Manifestos."""

    class PostType(models.TextChoices):
        GROWTH_LOG = 'GROWTH_LOG', _('Daily Growth Log')
        ESSAY = 'ESSAY', _('Deep Thought / Essay')
        VISION_BLOCK = 'VISION_BLOCK', _('Long-term Vision Statement')

    class LogCategory(models.TextChoices):
        LEARNING = "LEARNING", _("Study/Learning")
        WORK = "WORK", _("Project Work")
        LIFE = "LIFE", _("Personal/Habits")

    class Visibility(models.TextChoices):
        PUBLIC = "PUBLIC", _("Public")
        PRIVATE = "PRIVATE", _("Private")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='content_posts')

    post_type = models.CharField(max_length=20, choices=PostType.choices, db_index=True)
    title = models.CharField(max_length=200)
    content = models.TextField(_("Markdown Body"))

    category = models.CharField(max_length=50, choices=LogCategory.choices, blank=True, null=True)
    media_proof = models.ImageField(_("Proof of Work"), upload_to=content_media_path, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at', 'order']

    def __str__(self):
        return f"{self.get_post_type_display()} - {self.title}"


# Opportunities & Career Matching Layer

class UnifiedJobPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='job_preferences')
    role_title = models.CharField(max_length=100)
    work_arrangement = models.CharField(max_length=50)
    commitment_type = models.CharField(max_length=50)
    description = models.TextField(_("Preference Narrative"))
    is_active = models.BooleanField(default=True, db_index=True)


class LiveOpportunity(TimeStampedModel):
    """Ephemeral "Pings" to the network (e.g., 'Available for hire')."""
    class RequestType(models.TextChoices):
        MENTOR = 'MENTOR', _('Seeking a Mentor')
        HACKATHON = 'HACKATHON', _('Weekend Project Partner')
        FREELANCE = 'FREELANCE', _('Available for Freelance')
        COFOUNDER = 'COFOUNDER', _('Seeking Co-Founder')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='live_opportunities')

    request_type = models.CharField(max_length=20, choices=RequestType.choices, db_index=True)
    title = models.CharField(max_length=200)
    details = models.TextField()

    expires_at = models.DateTimeField(db_index=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['is_active', 'expires_at'])]

    @property
    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.expires_at is None:
            return True
        return self.expires_at > timezone.now()


# Right Now Social Ecosystem

class RightNowPost(TimeStampedModel):
    """The Core Feed Model for the "Right Now" ecosystem."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='right_now_posts')

    # Networking Intent
    current_search = models.CharField(
        _("Current Objective"),
        max_length=20, choices=SEARCH_OPTIONS, default='LEARNING', db_index=True,
        null=True, blank=True
    )
    collaboration_status = models.CharField(
        _("Availability"),
        max_length=20, choices=COLLAB_CHOICES, default='OPEN', db_index=True,
        null=True, blank=True
    )

    # Content
    title = models.CharField(_("Headline / Milestone"), max_length=200, blank=True, null=True)
    body_narrative = models.TextField(_("The Update (Markdown)"), blank=True, null=True)

    # 3. RICH LINK CACHING (The scalability secret for external links)
    external_link = models.URLField(_("External URL"), max_length=500, blank=True, null=True)
    link_title = models.CharField(max_length=255, blank=True, null=True)
    link_description = models.TextField(blank=True, null=True)
    link_image_url = models.URLField(max_length=500, blank=True, null=True)
    link_domain = models.CharField(max_length=100, blank=True, null=True)

    # Denormalized Metrics
    views_count = models.PositiveIntegerField(default=0)
    clicks_count = models.PositiveIntegerField(default=0, help_text=_("Clicks on external_link"))
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)

    # State & Visibility
    is_published = models.BooleanField(_("Show in Global Feed"), default=True, db_index=True)
    is_active_focus = models.BooleanField(
        _("Pinned to Profile Top"), default=True, db_index=True,
        help_text=_("If true, this is the current active status on their portfolio.")
    )
    is_admin_selected = models.BooleanField(
        _("Admin Curated"), default=False, db_index=True,
        help_text=_("If true, this post is selected by admin to appear in the feed.")
    )

    class Meta:
        verbose_name = _("Right Now Post")
        verbose_name_plural = _("Right Now Posts")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_published', '-created_at']),
            models.Index(fields=['is_active_focus', 'current_search']),
        ]

    def save(self, *args, **kwargs):
        # Handle Link Fetching (Only if link is new/changed)
        if self.external_link and not self.link_title:
            self._fetch_link_metadata()

        # Handle Profile Pinning Atomically
        with transaction.atomic():
            if self.is_active_focus:
                RightNowPost.objects.filter(profile=self.profile).exclude(pk=self.pk).update(is_active_focus=False)
                if self.profile_id:
                    UserProfile.objects.filter(pk=self.profile_id).update(last_signal_update=timezone.now())

            super().save(*args, **kwargs)

    def _fetch_link_metadata(self):
        """Scrapes Open Graph (OG) tags for link preview."""
        try:
            domain = urlparse(self.external_link).netloc
            self.link_domain = domain.replace("www.", "")

            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(self.external_link, headers=headers, timeout=2.5)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                og_title = soup.find("meta", property="og:title")
                og_desc = soup.find("meta", property="og:description")
                og_image = soup.find("meta", property="og:image")

                self.link_title = (og_title["content"] if og_title else (soup.title.string if soup.title else ""))[:250]
                self.link_description = (og_desc["content"] if og_desc else "")[:500]
                self.link_image_url = (og_image["content"] if og_image else "")[:500]

        except Exception as e:
            logger.warning(f"Metadata fetch failed for {self.external_link}: {str(e)}")
            pass

    def __str__(self):
        return f"{self.profile.user} - {self.current_search} ({self.created_at.strftime('%Y-%m-%d')})"


class RightNowMedia(models.Model):
    """Gallery Table for Right Now Posts."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(RightNowPost, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(_("Gallery Image"), upload_to=right_now_media_path)
    order_index = models.PositiveSmallIntegerField(default=0, db_index=True)

    class Meta:
        verbose_name = _("Right Now Media")
        verbose_name_plural = _("Right Now Media")
        ordering = ['order_index']

    def __str__(self):
        return f"Media for {self.post.id} (Order: {self.order_index})"


class RightNowLike(models.Model):
    """Tracks which profile liked which post (enforces one like per user)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(RightNowPost, on_delete=models.CASCADE, related_name='likes')
    profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='liked_posts')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Right Now Like"
        verbose_name_plural = "Right Now Likes"
        unique_together = ('post', 'profile')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.profile.user} liked {self.post.id}"


class RightNowComment(models.Model):
    """Stores user comments on Right Now Posts."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(RightNowPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='post_comments')
    body = models.TextField("Comment Body", max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Right Now Comment"
        verbose_name_plural = "Right Now Comments"
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.user} on {self.post.id}"


# System Automation & Signal Handlers

# Like Counters
@receiver(post_save, sender=RightNowLike)
def increment_likes_count(sender, instance, created, **kwargs):
    if created:
        RightNowPost.objects.filter(id=instance.post_id).update(likes_count=F('likes_count') + 1)

@receiver(post_delete, sender=RightNowLike)
def decrement_likes_count(sender, instance, **kwargs):
    RightNowPost.objects.filter(id=instance.post_id, likes_count__gt=0).update(likes_count=F('likes_count') - 1)

# Comment Counters
@receiver(post_save, sender=RightNowComment)
def increment_comments_count(sender, instance, created, **kwargs):
    if created:
        RightNowPost.objects.filter(id=instance.post_id).update(comments_count=F('comments_count') + 1)

@receiver(post_delete, sender=RightNowComment)
def decrement_comments_count(sender, instance, **kwargs):
    RightNowPost.objects.filter(id=instance.post_id, comments_count__gt=0).update(comments_count=F('comments_count') - 1)

# Async Image Optimization
def _perform_optimization(instance_id: Any, model_class: type, field_name: str) -> None:
    """Internal helper for image optimization post-commit."""
    try:
        instance = model_class.objects.get(pk=instance_id)
        image_field = getattr(instance, field_name)

        if not image_field or not hasattr(image_field, 'file'):
            return

        if not image_field.name.lower().endswith('.webp'):
            optimized = optimize_standard_image(image_field)
            if optimized:
                image_field.save(optimized.name, optimized, save=False)
                model_class.objects.filter(pk=instance.pk).update(**{field_name: image_field.name})

    except model_class.DoesNotExist:
        logger.warning(f"Optimization failed: {model_class.__name__} {instance_id} not found.")
    except Exception as e:
        logger.error(f"Image optimization error for {model_class.__name__} {instance_id}: {str(e)}")

@receiver(post_save, sender=ProjectGallery)
@receiver(post_save, sender=ContentPost)
@receiver(post_save, sender=RightNowMedia)
def optimize_portfolio_images_async(sender: Any, instance: Any, created: bool, **kwargs: Any) -> None:
    """Intercepts media uploads to run optimizations asynchronously."""
    target_fields = []

    if sender == ProjectGallery:
        target_fields.append('image')
    elif sender == ContentPost:
        target_fields.append('media_proof')
    elif sender == RightNowMedia: 
        target_fields.append('image')

    for field in target_fields:
        if getattr(instance, field, None):
            transaction.on_commit(
                lambda f=field: _perform_optimization(instance.pk, sender, f)
            )

