import uuid
from typing import Any
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from .utils import (
    MIN_YEAR,
    MAX_YEAR,
    company_cover_path,
    company_logo_path,
)


class Company(TimeStampedModel):
    """
    Independent Business Entity allowing decoupled management operations.
    """

    class Objective(models.TextChoices):
        BUILDING = "Expanding", "Expanding"
        FUNDRAISING = "FUNDRAISING", "Seeking Investment"
        HIRING = "HIRING", "Hiring"
        PARTNERING = "PARTNERING", "Seeking Co-Founders"
        SALES = "SALES", "Seeking B2B Clients"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(_("Company Slug"), unique=True, db_index=True)

    # --- Corporate Metadata ---
    name = models.CharField(_("Company Name"), max_length=200, db_index=True)
    sector = models.CharField(_("Sector/Industry"), max_length=100, db_index=True)
    location = models.CharField(_("Headquarters Location"), max_length=100)
    operating_since = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(MIN_YEAR), MaxValueValidator(MAX_YEAR)],
    )
    mission_stmt = models.TextField(_("Mission Statement"), blank=True)

    # --- Media Assets ---
    cover_image = models.ImageField(upload_to=company_cover_path, null=True, blank=True)
    logo = models.ImageField(
        _("Company Logo"), upload_to=company_logo_path, null=True, blank=True
    )

    # --- Business Objectives ---
    is_hiring = models.BooleanField(default=False)
    looking_for = models.CharField(
        max_length=20,
        choices=Objective.choices,
        default=Objective.BUILDING,
        verbose_name=_("Current Company Objective"),
    )

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ["-created_at"]

    def get_absolute_url(self) -> str:
        return reverse("company_public_profile", kwargs={"slug": self.slug})

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Auto-generates a globally unique slug from the company name."""
        if not self.slug:
            base_slug = slugify(self.name) or "company"
            slug = base_slug
            counter = 1
            while Company.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class CompanySocialLink(TimeStampedModel):
    # Add this line
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        "profiles.Company", on_delete=models.CASCADE, related_name="socials"
    )
    platform = models.CharField(max_length=50)
    url = models.URLField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "Company Social Link"


class CompanyContactMethod(TimeStampedModel):
    # Add this line
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        "profiles.Company", on_delete=models.CASCADE, related_name="contacts"
    )
    label = models.CharField(max_length=100)
    value = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Company Contact"


class CompanyMember(TimeStampedModel):
    """Junction table connecting Users to Companies with strict RBAC capabilities."""

    # 🚨 REQUIRED FOR UUID MIGRATION FIX 🚨
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Role(models.TextChoices):
        OWNER = "OWNER", _("Owner / Primary Contact")
        ADMIN = "ADMIN", _("Administrator")
        EDITOR = "EDITOR", _("Content Editor")
        ALUMNI = "ALUMNI", _("Past Member (No Access)")

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_memberships",
    )

    role = models.CharField(max_length=15, choices=Role.choices, default=Role.ADMIN)
    job_title = models.CharField(_("Job Title"), max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("company", "user")
        ordering = ["-role", "user__full_name"]

    def __str__(self) -> str:
        return f"{self.user.full_name} - {self.job_title} @ {self.company.name}"


class CompanyService(models.Model):
    """B2B Product and Services Catalog."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="services",
    )

    name = models.CharField(max_length=200)
    description = models.TextField(_("Deep Explanation"))
    is_active = models.BooleanField(default=True, db_index=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.company.name if self.company else 'No Company'})"


class ServiceGalleryImage(models.Model):
    """Visual gallery representing Company Services."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(
        CompanyService, on_delete=models.CASCADE, related_name="gallery"
    )
    image = models.ImageField(upload_to="companies/services/gallery/")
    caption = models.CharField(max_length=200, blank=True)

    def __str__(self) -> str:
        return f"Img: {self.service.name}"


class CompanyMilestone(models.Model):
    """Narrative Corporate Timeline records."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="milestones",
    )
    year = models.IntegerField()
    title = models.CharField(max_length=100)
    description = models.TextField()

    class Meta:
        ordering = ["-year"]

    def __str__(self) -> str:
        return f"{self.year}: {self.title}"


class CompanyNews(TimeStampedModel):
    """Corporate News, Press Releases, and Update Articles."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="news_articles",
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    content = models.TextField(_("Article Content"))
    excerpt = models.TextField(_("Short Summary"), blank=True)
    cover_image = models.ImageField(
        upload_to="companies/news/covers/", null=True, blank=True
    )

    is_published = models.BooleanField(default=True, db_index=True)
    published_date = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-published_date"]
        verbose_name = "Company News"
        verbose_name_plural = "Company News"

    def __str__(self) -> str:
        return f"{self.title} - {self.company.name if self.company else 'No Company'}"


class NewsGalleryImage(models.Model):
    """Embedded gallery system for Company News Articles."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    news = models.ForeignKey(
        CompanyNews, on_delete=models.CASCADE, related_name="gallery"
    )
    image = models.ImageField(upload_to="companies/news/gallery/")
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return f"Image for {self.news.title}"
