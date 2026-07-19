import logging
import uuid
from typing import Any, Final, Optional

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.templatetags.static import static
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from ..services import generate_corelink_id

logger = logging.getLogger(__name__)

PHONE_REGEX: Final[str] = r"^\+?1?\d{9,15}$"

phone_validator = RegexValidator(
    regex=PHONE_REGEX,
    message=_(
        "Phone number must be entered in the format: '+251911234567'. Up to 15 digits allowed."
    ),
)

DEFAULT_COVERS: Final[dict] = {
    "EXPERT": "img/defaults/covers/expert_blueprint.png",
    "VISIONARY": "img/defaults/covers/visionary_growth.png",
    "FOUNDER": "img/defaults/covers/founder_enterprise.png",
    "ADMIN": "img/defaults/covers/founder_enterprise.png",
}

DEFAULT_FALLBACK_COVER: Final[str] = "img/defaults/covers/generic_fallback.jpg"
DEFAULT_FALLBACK_AVATAR: Final[str] = "img/defaults/avatar_placeholder.webp"


class CustomUserManager(BaseUserManager):
    def create_user(
        self,
        phone_number: str,
        password: Optional[str] = None,
        **extra_fields: Any,
    ) -> "CustomUser":
        if not phone_number:
            raise ValueError(_("The Phone Number must be provided for authentication."))

        extra_fields.setdefault("is_active", True)
        phone_number = phone_number.strip()

        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        phone_number: str,
        password: Optional[str] = None,
        **extra_fields: Any,
    ) -> "CustomUser":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "ADMIN")

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(phone_number, password, **extra_fields)


class CustomUser(AbstractUser, TimeStampedModel):
    class Role(models.TextChoices):
        FOUNDER = "FOUNDER", _("Founder")
        EXPERT = "EXPERT", _("Expert")
        VISIONARY = "VISIONARY", _("Visionary")
        ADMIN = "ADMIN", _("Admin")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None

    phone_number = models.CharField(
        _("Phone Number"),
        max_length=15,
        unique=True,
        db_index=True,
        validators=[phone_validator],
        error_messages={"unique": _("A user with this phone number already exists.")},
        help_text=_("Primary authentication identifier. Format: +251911234567"),
    )
    email = models.EmailField(
        _("Email Address"),
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Used for OTP verification and Google sign-in"),
    )

    corelink_id = models.CharField(
        _("Public Badge"),
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Human-readable unique ID (e.g., VIS-2024-001). Auto-generated."),
    )

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.VISIONARY,
        db_index=True,
        help_text=_("Determines platform access and profile features"),
    )
    full_name = models.CharField(
        _("Legal Name"),
        max_length=150,
        help_text=_("Official name for professional correspondence"),
    )
    email = models.EmailField(
        _("Email Address"),
        unique=True,
        null=True,
        blank=True,
        help_text=_("Primary email for notifications and account recovery"),
    )
    is_email_verified = models.BooleanField(
        _("Email Verified"),
        default=False,
        help_text=_("Indicates if the user's primary email has been verified"),
    )
    email_otp = models.CharField(
        _("Email OTP"),
        max_length=128,
        null=True,
        blank=True,
        help_text=_("One-time password for email verification"),
    )
    email_otp_created_at = models.DateTimeField(
        _("OTP Created At"),
        null=True,
        blank=True,
        help_text=_("Timestamp when the email OTP was generated"),
    )
    telegram_handle = models.CharField(
        _("Telegram Handle"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("@username for community communication"),
    )
    country = models.ForeignKey(
        "accounts.Country",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        help_text=_("User country selected from verified countries"),
    )
    city = models.ForeignKey(
        "accounts.City",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        help_text=_("User city selected from verified cities"),
    )
    current_location = models.CharField(
        _("Current Location"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("City, Country for networking purposes"),
    )

    avatar = models.ImageField(
        _("Avatar"),
        upload_to="public/avatars/",
        null=True,
        blank=True,
        help_text=_("Profile picture. Auto-optimized to WebP format"),
    )
    cover_image = models.ImageField(
        _("Cover Image"),
        upload_to="public/covers/",
        null=True,
        blank=True,
        help_text=_("Header image. Role-based fallbacks available"),
    )

    is_verified = models.BooleanField(
        _("Verification Status"),
        default=False,  # Reverted to False
        help_text=_("Identity verification completion status"),
    )
    profile_verified = models.BooleanField(
        _("Profile Verified"),
        default=False,
        help_text=_("Check this to mark the user's profile as verified on the public portfolio page"),
    )
    google_sub = models.CharField(
        _("Google Subject ID"),
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        help_text=_("Unique Google account subject identifier"),
    )
    is_active = models.BooleanField(
        _("Active Switch"),
        default=True,
        help_text=_("Account suspension control"),
    )
    is_public = models.BooleanField(
        _("Public Visibility"),
        default=True,
        help_text=_(
            "If unchecked, user vanishes from Network/Nexus but can apply to jobs"
        ),
    )
    is_nexus_visible = models.BooleanField(
        _("Public Feed"),
        default=True,
        help_text=_("Uncheck to ban user from public Nexus feed"),
    )
    is_selected = models.BooleanField(
        _("Admin Pick"),
        default=False,
        db_index=True,
        help_text=_("Pin this user to the top of the Nexus Feed"),
    )
    
    # Right Now Feed Controls
    is_pinned_in_right_now = models.BooleanField(
        _("Pinned in Right Now Feed"),
        default=False,
        db_index=True,
        help_text=_("Pin this user to the top of the Right Now feed"),
    )
    is_banned_from_right_now = models.BooleanField(
        _("Banned from Right Now Feed"),
        default=False,
        db_index=True,
        help_text=_("Hide this user from the Right Now feed"),
    )
    
    # Home Page Curation Controls
    is_hero_avatar_selected = models.BooleanField(
        _("Hero Avatar"),
        default=False,
        db_index=True,
        help_text=_("Pin this user to the hero section on landing page"),
    )
    is_home_profile_selected = models.BooleanField(
        _("Home Profile"),
        default=False,
        db_index=True,
        help_text=_("Pin this user to the Talent Network section on landing page"),
    )
    is_top_10 = models.BooleanField(
        _("Top 10 Talent"),
        default=False,
        db_index=True,
        help_text=_("Pin this user to the Top 10 section on Nexus Feed"),
    )
    home_page_top = models.BooleanField(
        _("Home Page Top"),
        default=False,
        db_index=True,
        help_text=_("Pin this user to the top section of home page"),
    )
    is_contacted = models.BooleanField(
        _("Contacted Status"),
        default=False,
        db_index=True,
        help_text=_("Check this if the user has been reached out to by our team.")
    )
    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["full_name"]
    objects = CustomUserManager()

    class Meta:
        verbose_name = _("Custom User")
        verbose_name_plural = _("Custom Users")
        db_table = "corelink_identity_user"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone_number"]),
            models.Index(fields=["corelink_id"]),
            models.Index(fields=["role", "is_public"]),
            models.Index(fields=["is_selected", "created_at"]),
        ]

    @property
    def display_name(self) -> str:
        first_name = (self.first_name or "").strip()
        last_name = (self.last_name or "").strip()
        combined_name = f"{first_name} {last_name}".strip()
        if combined_name:
            return combined_name
        return (self.full_name or "").strip() or str(self.phone_number)

    def get_full_name(self) -> str:
        return self.display_name

    def get_short_name(self) -> str:
        return (self.first_name or "").strip() or self.display_name

    # Compatibility aliases used by newer auth flow code.
    @property
    def email_verified(self) -> bool:
        return bool(self.is_email_verified)

    @email_verified.setter
    def email_verified(self, value: bool) -> None:
        self.is_email_verified = bool(value)

    @property
    def email_otp_code(self):
        return self.email_otp

    @email_otp_code.setter
    def email_otp_code(self, value) -> None:
        self.email_otp = value

    @property
    def email_otp_expires_at(self):
        return self.email_otp_created_at

    @email_otp_expires_at.setter
    def email_otp_expires_at(self, value) -> None:
        self.email_otp_created_at = value

    def __str__(self) -> str:
        return f"{self.display_name} ({self.corelink_id or self.phone_number})"

    def get_absolute_url(self) -> str:
        """Returns the URL for the user's Unified Portfolio."""
        slug = None

        try:
            if hasattr(self, "portfolio") and self.portfolio.slug:
                slug = self.portfolio.slug
        except Exception as e:
            logger.warning(f"Error resolving absolute URL for user {self.id}: {e}")

        identifier = slug or self.corelink_id or str(self.id)
        return reverse("public_profile", kwargs={"identifier": identifier})

    @property
    def get_avatar_url(self) -> str:
        try:
            if self.avatar and self.avatar.name and hasattr(self.avatar, "storage"):
                if self.avatar.storage.exists(self.avatar.name):
                    return self.avatar.url
        except Exception:
            pass
        return static(DEFAULT_FALLBACK_AVATAR)

    @property
    def get_cover_image_url(self) -> str:
        try:
            if self.cover_image and hasattr(self.cover_image, "url"):
                return self.cover_image.url
        except Exception:
            pass

        role_key = self.role if self.role else "VISIONARY"
        return static(DEFAULT_COVERS.get(role_key, DEFAULT_FALLBACK_COVER))

    def save(self, *args: Any, **kwargs: Any) -> None:
        # Translate compatibility alias names when callers use update_fields.
        if "update_fields" in kwargs and kwargs["update_fields"] is not None:
            field_aliases = {
                "email_verified": "is_email_verified",
                "email_otp_code": "email_otp",
                "email_otp_expires_at": "email_otp_created_at",
            }
            translated = set()
            for field in kwargs["update_fields"]:
                translated.add(field_aliases.get(field, field))
            kwargs["update_fields"] = list(translated)

        if not self.corelink_id and self.role:
            try:
                self.corelink_id = generate_corelink_id(self.role)
            except Exception as e:
                logger.error(
                    f"Failed to generate CoreLink ID for {self.phone_number}: {e}"
                )
        super().save(*args, **kwargs)


class StaffUser(CustomUser):
    class Meta:
        proxy = True
        verbose_name = _("Admin Staff")
        verbose_name_plural = _("Admin Staff")

    objects = CustomUserManager()
