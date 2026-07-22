import uuid
from typing import Any
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel


def service_gallery_path(instance: Any, filename: str) -> str:
    """Upload path for service gallery images."""
    ext = filename.split('.')[-1]
    return f"portfolio/services/{instance.service.profile.pk}/{uuid.uuid4().hex[:12]}.{ext}"


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
