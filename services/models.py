import uuid
from typing import Any
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from core.models import TimeStampedModel


def service_gallery_path(instance: Any, filename: str) -> str:
    """Upload path for service gallery images."""
    ext = filename.split('.')[-1]
    return f"portfolio/services/{instance.service.profile.pk}/{uuid.uuid4().hex[:12]}.{ext}"


def category_icon_path(instance: Any, filename: str) -> str:
    """Upload path for category icons."""
    ext = filename.split('.')[-1]
    return f"categories/icons/{uuid.uuid4().hex[:12]}.{ext}"


class ServiceCategory(TimeStampedModel):
    """Primary categories for service classification (Design, Development, Marketing, etc.)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Category Name"), max_length=100, unique=True, db_index=True)
    slug = models.SlugField(_("Slug"), max_length=120, unique=True, allow_unicode=True)
    description = models.TextField(_("Description"), blank=True, help_text=_("Brief description of this category"))
    icon = models.ImageField(_("Icon"), upload_to=category_icon_path, blank=True, null=True)
    color = models.CharField(_("Accent Color"), max_length=7, default='#2563EB', help_text=_("Hex color code for category branding"))
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = _("Service Category")
        verbose_name_plural = _("Service Categories")

    def __str__(self):
        return self.name

    def clean(self):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)


class ServiceSubcategory(TimeStampedModel):
    """Nested subcategories for granular filtering within primary categories."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name='subcategories',
        verbose_name=_("Parent Category")
    )
    name = models.CharField(_("Subcategory Name"), max_length=100, db_index=True)
    slug = models.SlugField(_("Slug"), max_length=120, allow_unicode=True)
    description = models.TextField(_("Description"), blank=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['category', 'order', 'name']
        verbose_name = _("Service Subcategory")
        verbose_name_plural = _("Service Subcategories")
        unique_together = [['category', 'slug']]

    def __str__(self):
        return f"{self.category.name} > {self.name}"

    def clean(self):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)


class ServiceTag(TimeStampedModel):
    """Flexible tags for cross-category discovery and keyword-based filtering."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Tag Name"), max_length=50, unique=True, db_index=True)
    slug = models.SlugField(_("Slug"), max_length=60, unique=True, allow_unicode=True)
    description = models.CharField(_("Description"), max_length=200, blank=True)
    is_featured = models.BooleanField(default=False, help_text=_("Featured tags are highlighted in the UI"))
    usage_count = models.PositiveIntegerField(default=0, help_text=_("Track popularity of this tag"))

    class Meta:
        ordering = ['-usage_count', 'name']
        verbose_name = _("Service Tag")
        verbose_name_plural = _("Service Tags")

    def __str__(self):
        return self.name

    def clean(self):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)


class ServiceType(TimeStampedModel):
    """Service delivery types (One-time, Recurring, Consultation, Maintenance)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Type Name"), max_length=50, unique=True, db_index=True)
    slug = models.SlugField(_("Slug"), max_length=60, unique=True, allow_unicode=True)
    description = models.TextField(_("Description"), help_text=_("Explain what this service type means"))
    icon = models.CharField(_("Icon"), max_length=50, blank=True, help_text=_("Icon class or emoji"))
    order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = _("Service Type")
        verbose_name_plural = _("Service Types")

    def __str__(self):
        return self.name

    def clean(self):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)


class Service(TimeStampedModel):
    """Professional services offered by users - distinct from company services."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        'profiles.UserProfile',
        on_delete=models.CASCADE,
        related_name='service_listings'
    )

    title = models.CharField(_("Service Title"), max_length=200, db_index=True)
    description = models.TextField(_("Service Description"), help_text=_("Explain your service in detail"))

    # Category system (optional for backward compatibility)
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        related_name='services',
        verbose_name=_("Primary Category"),
        null=True,
        blank=True,
        help_text=_("Main category for this service")
    )
    subcategory = models.ForeignKey(
        ServiceSubcategory,
        on_delete=models.SET_NULL,
        related_name='services',
        verbose_name=_("Subcategory"),
        null=True,
        blank=True,
        help_text=_("More specific classification within category")
    )
    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.SET_NULL,
        related_name='services',
        verbose_name=_("Service Type"),
        null=True,
        blank=True,
        help_text=_("How this service is delivered")
    )
    tags = models.ManyToManyField(
        ServiceTag,
        related_name='services',
        verbose_name=_("Tags"),
        blank=True,
        help_text=_("Keywords for cross-category discovery")
    )

    is_active = models.BooleanField(default=True, db_index=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = _("Service")
        verbose_name_plural = _("Services")

    def __str__(self):
        return f"{self.title} ({self.profile.user.full_name if self.profile.user else 'No User'})"

    def clean(self):
        """Validate that subcategory belongs to the selected category."""
        if self.subcategory and self.category:
            if self.subcategory.category != self.category:
                raise ValidationError({
                    'subcategory': _("Subcategory must belong to the selected category.")
                })


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
