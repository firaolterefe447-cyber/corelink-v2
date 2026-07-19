"""
CoreLink Opportunities Platform

Professional career and project marketplace with intelligent job matching,
challenge-based hiring, AI-powered recommendations, and application tracking.
"""

from profiles.models import Company

# System Imports & Dependencies
import uuid
from django.db import models
from django.db.models import F
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

# Internal Dependencies
from core.models import TimeStampedModel

# Skill Taxonomy System

class Skill(TimeStampedModel):
    """AI-ready skill taxonomy system for intelligent matching."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=50, 
        unique=True,
        help_text=_("Canonical skill name for matching")
    )
    slug = models.SlugField(
        max_length=50, 
        unique=True, 
        blank=True,
        help_text=_("URL-friendly skill identifier")
    )
    
    # 🤖 AI Readiness Features
    ai_aliases = models.JSONField(
        default=list, 
        blank=True,
        help_text=_("AI synonyms for semantic matching (e.g., ['VueJS', 'Vue.js'])")
    )
    category = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text=_("Skill category for organization (e.g., 'Engineering', 'Design')")
    )
    description = models.TextField(
        blank=True,
        help_text=_("Detailed skill description for AI context")
    )
    proficiency_levels = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Available proficiency levels (e.g., ['Junior', 'Senior', 'Expert'])")
    )
    is_trending = models.BooleanField(
        default=False,
        help_text=_("Mark as trending skill for highlighting")
    )

    class Meta:
        verbose_name = "Skill"
        verbose_name_plural = "Skills"
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category']),
            models.Index(fields=['is_trending']),
        ]

    def save(self, *args, **kwargs):
        """Auto-generate slug and normalize data"""
        if not self.slug:
            self.slug = slugify(self.name)
        
        # Normalize AI aliases
        if self.ai_aliases:
            self.ai_aliases = [alias.strip() for alias in self.ai_aliases if alias.strip()]
        
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

    def get_all_variants(self):
        """
        Get all name variants including AI aliases.
        
        Returns:
            list: All skill name variations for matching
        """
        variants = [self.name.lower()]
        if self.ai_aliases:
            variants.extend([alias.lower() for alias in self.ai_aliases])
        return list(set(variants))

    @property
    def display_name(self):
        """Get the best display name for UI"""
        return self.name

# ═══════════════════════════════════════════════════════════════════════════════
# # 2. MASTER OPPORTUNITY MODEL
# ═══════════════════════════════════════════════════════════════════════════════

class JobPost(TimeStampedModel):
    """Comprehensive opportunity management for diverse job types and workflows."""

    # Opportunity Classification
    class JobType(models.TextChoices):
        """Comprehensive opportunity type classification"""
        FULL_TIME = 'FULL_TIME', _('Full-Time Role')
        PART_TIME = 'PART_TIME', _('Part-Time Role')
        INTERNSHIP = 'INTERNSHIP', _('Internship')
        CONTRACT = 'CONTRACT', _('Freelance / Contract')
        GIG = 'GIG', _('Gig / Quick Task')
        CHALLENGE = 'CHALLENGE', _('Business Challenge')
        ADVISORY = 'ADVISORY', _('Advisory / Mentorship')
        VOLUNTEER = 'VOLUNTEER', _('Volunteer / Social Impact')
        COFOUNDER = 'COFOUNDER', _('Co-Founder')

    class Status(models.TextChoices):
        """Publication and workflow status management"""
        DRAFT = 'DRAFT', _('Draft')
        PENDING = 'PENDING', _('Pending Approval')
        ACTIVE = 'ACTIVE', _('Live')
        CLOSED = 'CLOSED', _('Closed')
        REJECTED = 'REJECTED', _('Rejected')

    class ExperienceLevel(models.TextChoices):
        """Experience level requirements for filtering"""
        STUDENT = 'STUDENT', _('Student / Intern')
        ENTRY = 'ENTRY', _('Entry Level / Junior')
        MID = 'MID', _('Mid Level')
        SENIOR = 'SENIOR', _('Senior Level')
        LEAD = 'LEAD', _('Lead / Manager')
        EXECUTIVE = 'EXECUTIVE', _('Executive / Director')
        ANY = 'ANY', _('Any Level / Not Applicable')

    # System Identity & SEO
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(
        max_length=255, 
        unique=True, 
        blank=True,
        help_text=_("SEO-friendly URL. Auto-generated from title.")
    )

    # Source & Attribution
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='created_opportunities',
        help_text=_("User who posted this opportunity")
    )
    submitter_contact = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text=_("Guest contact info (Telegram handle, Phone, or Email) for admin communication")
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='opportunities', 
        null=True, 
        blank=True,
        help_text=_("Company offering this opportunity")
    )
    is_official_admin_post = models.BooleanField(
        default=False,
        help_text=_("Mark as official CoreLink platform posting")
    )

    # EXTERNAL POST HANDLING (For Cold Start Seeding)
    is_external = models.BooleanField(
        default=False, 
        help_text=_("Is this an outside application opportunity?")
    )
    external_url = models.URLField(
        max_length=500, 
        blank=True, 
        null=True,
        help_text=_("Optional link to external application page")
    )
    external_company_name = models.CharField(
        max_length=200, 
        blank=True,
        help_text=_("Company name for external postings")
    )
    external_company_logo = models.ImageField(
        upload_to='opportunities/logos/', 
        null=True, 
        blank=True,
        help_text=_("Company logo for external postings")
    )
    source_name = models.CharField(
        max_length=100, 
        blank=True,
        help_text=_("Source platform (e.g., 'Telegram', 'EthioJobs')")
    )

    # Content & Description
    title = models.CharField(
        max_length=200,
        help_text=_("Clear, descriptive job title")
    )
    description = models.TextField(
        _("The Mission Narrative"), 
        blank=True,
        help_text=_("Detailed job description. Markdown supported.")
    )
    cover_image = models.ImageField(
        upload_to='opportunities/covers/', 
        null=True, 
        blank=True,
        help_text=_("Optional cover image for visual appeal")
    )

    # Classification & Metadata
    job_type = models.CharField(
        max_length=20, 
        choices=JobType.choices, 
        default=JobType.FULL_TIME,
        help_text=_("Type of opportunity")
    )
    level = models.CharField(
        max_length=20,
        choices=ExperienceLevel.choices,
        null=True,
        blank=True,
        help_text=_("Required experience level")
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING,
        help_text=_("Publication status")
    )
    published_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text=_("Publication timestamp for sorting")
    )

    # Location Configuration
    location = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        default="Addis Ababa",
        help_text=_("Job location or 'Remote'")
    )
    is_remote = models.BooleanField(
        default=False,
        help_text=_("Remote work opportunity")
    )

    # Financial Information
    compensation_text = models.CharField(
        max_length=100, 
        blank=True,
        help_text=_("Compensation description (e.g., 'Competitive', 'Negotiable')")
    )
    salary_min = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text=_("Minimum salary (annual or hourly as appropriate)")
    )
    salary_max = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text=_("Maximum salary (annual or hourly as appropriate)")
    )

    # Deadline Management
    deadline_date = models.DateField(
        null=True, 
        blank=True,
        help_text=_("Specific deadline date for calendar sorting")
    )
    deadline_text = models.CharField(
        max_length=150, 
        blank=True,
        help_text=_("Flexible deadline description (e.g., 'Rolling basis', 'ASAP')")
    )
    is_open_ended = models.BooleanField(
        default=True,
        help_text=_("No specific deadline - always accepting applications")
    )

    # CoreLink Innovation (Challenge Mode)
    requires_challenge = models.BooleanField(
        default=False,
        help_text=_("Require applicants to complete a challenge")
    )
    challenge_description = models.TextField(
        blank=True,
        help_text=_("Detailed challenge requirements (e.g., 'Attach a React hooks project')")
    )

    # Skills & AI Metadata
    required_skills = models.ManyToManyField(
        'Skill', 
        blank=True, 
        related_name='opportunities',
        help_text=_("Required skills for matching")
    )
    views_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Total views for analytics")
    )
    applications_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Total applications received")
    )

    # AI & Future Readiness
    ai_metadata = models.JSONField(
        default=dict, 
        blank=True,
        help_text=_("AI analysis data, embeddings, and semantic search info")
    )
    ai_match_score = models.FloatField(
        default=0.0,
        help_text=_("AI-calculated quality score (0-100)")
    )

    class Meta:
        ordering = ['-published_at', '-created_at']
        verbose_name = "Job Opportunity"
        verbose_name_plural = "Job Opportunities"
        indexes = [
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['job_type', 'is_remote']),
            models.Index(fields=['level']),
            models.Index(fields=['deadline_date']),
            models.Index(fields=['is_open_ended']),
            models.Index(fields=['ai_match_score']),
        ]

    def save(self, *args, **kwargs):
        """Enhanced save method with auto-generation and validation."""
        # Auto-generate SEO friendly Slug
        if not self.slug:
            base_slug = slugify(self.title)
            short_id = str(self.id).split('-')[0]
            self.slug = f"{base_slug}-{short_id}"

        # Auto-set published timestamp when status changes to ACTIVE
        if self.status == self.Status.ACTIVE and not self.published_at:
            self.published_at = timezone.now()

        # Smart deadline resolution
        self._resolve_deadline_logic()

        super().save(*args, **kwargs)

    def _resolve_deadline_logic(self):
        """Intelligent deadline management with auto-correction."""
        if self.deadline_date or self.deadline_text:
            self.is_open_ended = False
        elif not self.deadline_date and not self.deadline_text:
            self.is_open_ended = True

    def clean(self):
        """Comprehensive validation with smart error handling."""
        super().clean()
        errors = []
        row_id = self.title if self.title else "New Job"

        # Challenge requirement validation
        if self.requires_challenge and not self.challenge_description:
            errors.append(f"[{row_id}] Challenge missing: Please describe the challenge requirements.")

        # Salary range validation
        if self.salary_min and self.salary_max and self.salary_min > self.salary_max:
            errors.append(f"[{row_id}] Salary Error: Minimum salary cannot be greater than maximum.")

        # External posting validation
        if self.is_external and not self.external_company_name:
            errors.append(f"[{row_id}] External posting requires company name.")

        if errors:
            raise ValidationError(errors)

    def increment_view(self):
        """Thread-safe view counter increment"""
        JobPost.objects.filter(pk=self.pk).update(views_count=F('views_count') + 1)
        self.refresh_from_db(fields=['views_count'])

    def __str__(self) -> str:
        return f"{self.title} @ {self.get_company_name()}"

    # Helper Methods & Properties
    def get_company_name(self):
        """Get the best available company name"""
        if self.company:
            return self.company.name
        return self.external_company_name or "Unknown Entity"

    def get_company_logo(self):
        """Get the best available company logo"""
        if self.company and self.company.logo:
            return self.company.logo.url
        if self.external_company_logo:
            return self.external_company_logo.url
        return None

    @property
    def attribution_type(self):
        """Determine the attribution source"""
        if self.is_official_admin_post:
            return "ADMIN"
        elif self.company:
            return "COMPANY"
        return "USER"

    @property
    def is_urgent(self):
        """Determine if this is an urgent opportunity"""
        if not self.is_open_ended and self.deadline_date:
            days_remaining = (self.deadline_date - timezone.now().date()).days
            return days_remaining <= 7
        return False

    @property
    def salary_range_display(self):
        """Get formatted salary range"""
        if self.salary_min and self.salary_max:
            return f"${self.salary_min:,.0f} - ${self.salary_max:,.0f}"
        elif self.salary_min:
            return f"From ${self.salary_min:,.0f}"
        elif self.compensation_text:
            return self.compensation_text
        return "Competitive"

    def get_absolute_url(self):
        """Generate the absolute URL for this opportunity"""
        from django.urls import reverse
        return reverse('opportunities:detail', kwargs={'slug': self.slug})

# Application Management System

class JobApplication(TimeStampedModel):
    """Advanced application management with AI-powered matching and proof-of-work."""

    class Status(models.TextChoices):
        """Application workflow status tracking"""
        LINKED = 'LINKED', _('Linked')
        VIEWED = 'VIEWED', _('Recruiter Viewed')
        SHORTLISTED = 'SHORTLISTED', _('Shortlisted')
        INTERVIEW = 'INTERVIEW', _('Interview')
        REJECTED = 'REJECTED', _('Not a Fit')
        HIRED = 'HIRED', _('Hired')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(
        JobPost, 
        on_delete=models.CASCADE, 
        related_name='applications',
        help_text=_("Target opportunity")
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='job_applications',
        help_text=_("Applicant user")
    )

    # Application Content
    cover_note = models.TextField(
        max_length=2000, 
        blank=True,
        help_text=_("Personalized cover letter and motivation")
    )

    # THE CORE LINK INNOVATION: Proof of Work
    attached_project = models.ForeignKey(
        'profiles.PortfolioProject',
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        help_text=_("Portfolio project demonstrating relevant skills")
    )

    # Status & Workflow
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.LINKED,
        help_text=_("Current application status")
    )

    # AI Match Logic
    match_score = models.FloatField(
        default=0.0, 
        help_text=_("AI compatibility score (0-100)")
    )
    ai_analysis = models.JSONField(
        default=dict, 
        blank=True,
        help_text=_("Detailed AI analysis and reasoning")
    )

    class Meta:
        unique_together = ('job', 'applicant')
        ordering = ['-match_score', '-created_at']
        verbose_name = "Job Application"
        verbose_name_plural = "Job Applications"
        indexes = [
            models.Index(fields=['job', 'status']),
            models.Index(fields=['applicant', 'status']),
            models.Index(fields=['match_score']),
            models.Index(fields=['status', 'created_at']),
        ]

    def clean(self):
        """Application validation with challenge requirements."""
        if self.job.requires_challenge and not self.attached_project:
            raise ValidationError({
                'attached_project': _('This role requires you to attach a project/proof of work.')
            })

    def save(self, *args, **kwargs):
        """Enhanced save with automatic application counting."""
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Safely increment application count on the job
        if is_new:
            JobPost.objects.filter(pk=self.job.pk).update(applications_count=F('applications_count') + 1)

    def __str__(self) -> str:
        applicant_name = self.applicant.get_full_name() or self.applicant.username
        return f"{applicant_name} → {self.job.title}"

    # AI Matching & Analysis
    def calculate_match_score(self):
        """Calculate AI-powered compatibility score."""
        # Placeholder for AI matching algorithm
        # This would integrate with the AI service
        score = 75.0  # Base score
        
        # Skill matching bonus
        if self.attached_project:
            score += 10
        
        # Challenge completion bonus
        if self.job.requires_challenge and self.attached_project:
            score += 15
        
        self.match_score = min(score, 100.0)
        self.save(update_fields=['match_score'])
        
        return self.match_score

    def advance_status(self, new_status):
        """Advance application through workflow stages."""
        valid_transitions = {
            self.Status.LINKED: [self.Status.VIEWED, self.Status.REJECTED],
            self.Status.VIEWED: [self.Status.SHORTLISTED, self.Status.REJECTED, self.Status.INTERVIEW],
            self.Status.SHORTLISTED: [self.Status.INTERVIEW, self.Status.REJECTED],
            self.Status.INTERVIEW: [self.Status.HIRED, self.Status.REJECTED],
        }
        
        if new_status not in valid_transitions.get(self.status, []):
            raise ValueError(f"Invalid status transition from {self.status} to {new_status}")
        
        self.status = new_status
        self.save()

    @property
    def is_active(self):
        """Check if application is still in active consideration"""
        return self.status in [self.Status.LINKED, self.Status.VIEWED, self.Status.SHORTLISTED, self.Status.INTERVIEW]

    @property
    def success_probability(self):
        """Get AI-predicted success probability"""
        # This would be calculated by the AI service
        return self.match_score / 100.0
