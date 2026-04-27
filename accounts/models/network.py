import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from .user import CustomUser

class FieldOfInterest(models.Model):
    name = models.CharField(max_length=255, unique=True, db_index=True)

    def __str__(self):
        return self.name


class CurrentStatus(models.Model):
    name = models.CharField(max_length=255, unique=True, db_index=True)

    def __str__(self):
        return self.name

class UniversalSocialLink(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="social_links",
        db_index=True,
        help_text=_("User who owns this social link"),
    )
    platform_name = models.CharField(
        _("Platform"),
        max_length=50,
        help_text=_("e.g., LinkedIn, Twitter, GitHub"),
    )
    url = models.URLField(
        _("URL Payload"),
        max_length=500,
        help_text=_("Full URL to the social profile"),
    )
    icon_slug = models.CharField(
        max_length=50,
        default="link",
        help_text=_("Icon identifier for UI rendering"),
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text=_("Display order on profile"),
    )

    class Meta:
        ordering = ["order"]
        verbose_name = _("Social Link")
        verbose_name_plural = _("Social Links")
        indexes = [
            models.Index(fields=["user", "order"]),
            models.Index(fields=["platform_name"]),
        ]

    def __str__(self) -> str:
        return f"{self.platform_name}: {self.user.full_name}"


class UniversalContactMethod(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="contact_methods",
        db_index=True,
        help_text=_("User who owns this contact method"),
    )
    type = models.CharField(
        _("Platform / Method"),
        max_length=50,
        help_text=_("e.g., Email, Phone, WhatsApp, Telegram"),
    )
    value = models.CharField(
        _("Contact Value"),
        max_length=255,
        help_text=_("Actual contact information (address, number, handle)"),
    )

    class Meta:
        verbose_name = _("Contact Method")
        verbose_name_plural = _("Contact Methods")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "type"]),
        ]

    def __str__(self) -> str:
        return f"{self.type}: {self.value}"

    @property
    def icon_name(self) -> str:
        t = self.type.lower()
        icon_map = {
            "mail": "mail",
            "phone": "phone",
            "mobile": "phone",
            "call": "phone",
            "telegram": "send",
            "whatsapp": "message-circle",
            "linkedin": "linkedin",
            "twitter": "twitter",
            "x": "twitter",
            "github": "github",
            "web": "globe",
            "site": "globe",
            "portfolio": "globe",
            "location": "map-pin",
            "address": "map-pin",
            "office": "map-pin",
        }

        for key, icon in icon_map.items():
            if key in t:
                return icon
        return "contact"
