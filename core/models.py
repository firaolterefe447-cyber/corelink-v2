"""
CoreLink Foundation Models

Foundational models providing base functionality for the entire CoreLink platform.
Includes abstract base classes, media management, and system-wide utilities.
"""

# System Imports & Dependencies
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

# Abstract Base Classes

class TimeStampedModel(models.Model):
    """Abstract base class providing automatic timestamp tracking."""
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp when the record was created")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_("Timestamp when the record was last updated")
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]

# Site Assets Management

class SiteMediaAsset(TimeStampedModel):
    """Centralized management of platform media assets and promotional content."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zone_slug = models.CharField(
        max_length=100,
        help_text=_("Zone identifier (e.g., HOME_HERO, SIDEBAR_BANNER)")
    )
    title = models.CharField(
        max_length=200, 
        blank=True,
        help_text=_("Optional title for admin reference")
    )
    image = models.ImageField(
        upload_to='public/assets/',
        help_text=_("Media asset file. Optimized for web display")
    )
    target_link = models.URLField(
        blank=True,
        help_text=_("Optional click-through URL for the asset")
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text=_("Display order within the zone")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Controls visibility on the platform")
    )

    class Meta:
        ordering = ['zone_slug', 'order']
        verbose_name = "Site Media Asset"
        verbose_name_plural = "Site Media Assets"
        indexes = [
            models.Index(fields=['zone_slug', 'order', 'is_active']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        """Human-readable representation with zone context"""
        return f"{self.zone_slug} - {self.title or 'Untitled'}"

    def get_absolute_url(self):
        """Returns the target link or None"""
        return self.target_link if self.target_link else None

    @property
    def is_clickable(self):
        """Check if the asset has a valid target link"""
        return bool(self.target_link)

class SiteTextAsset(models.Model):
    """Dynamic text content management for platform customization."""
    key = models.CharField(
        max_length=100, 
        primary_key=True,
        help_text=_("Unique identifier for the text content")
    )
    content = models.TextField(
        help_text=_("Text content. Supports HTML for rich formatting")
    )
    description = models.CharField(
        max_length=255, 
        blank=True,
        help_text=_("Admin description for content identification")
    )
    is_rich_text = models.BooleanField(
        default=False,
        help_text=_("Enable HTML rendering for this content")
    )

    class Meta:
        verbose_name = "Site Text Asset"
        verbose_name_plural = "Site Text Assets"
        indexes = [
            models.Index(fields=['key']),
        ]

    def __str__(self):
        """Human-readable representation"""
        return self.key

    def render(self):
        """
        Render content based on text type.
        
        Returns:
            str: Rendered content (plain text or HTML)
        """
        if self.is_rich_text:
            return self.content
        return self.escape_html(self.content)

    @staticmethod
    def escape_html(text):
        """
        Basic HTML escaping for security.
        
        Args:
            text (str): Text to escape
            
        Returns:
            str: HTML-escaped text
        """
        import html
        return html.escape(text)

    @classmethod
    def get_content(cls, key, default=""):
        """
        Retrieve content by key with fallback.
        
        Args:
            key (str): Content identifier
            default (str): Fallback content if not found
            
        Returns:
            str: Content or default value
        """
        try:
            asset = cls.objects.get(key=key)
            return asset.render()
        except cls.DoesNotExist:
            return default

# ═══════════════════════════════════════════════════════════════════════════════
# # 3. UTILITY FUNCTIONS & HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_active_media_assets(zone_slug=None):
    """
    Retrieve active media assets with optional zone filtering.
    
    Args:
        zone_slug (str, optional): Filter by specific zone
        
    Returns:
        QuerySet: Active media assets ordered by zone and order
    """
    queryset = SiteMediaAsset.objects.filter(is_active=True)
    if zone_slug:
        queryset = queryset.filter(zone_slug=zone_slug)
    return queryset.order_by('zone_slug', 'order')

def get_site_text_content(key, default=""):
    """
    Convenience function to retrieve site text content.
    
    Args:
        key (str): Content identifier
        default (str): Fallback content
        
    Returns:
        str: Content or default value
    """
    return SiteTextAsset.get_content(key, default)

# ═══════════════════════════════════════════════════════════════════════════════
# # 4. MODEL ADMINISTRATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

class AssetManager(models.Manager):
    """
    Custom manager for SiteMediaAsset with common query patterns.
    """
    
    def active(self):
        """Return only active assets"""
        return self.filter(is_active=True)
    
    def by_zone(self, zone_slug):
        """Return assets for a specific zone"""
        return self.filter(zone_slug=zone_slug)
    
    def ordered(self):
        """Return assets ordered by zone and order"""
        return self.order_by('zone_slug', 'order')

# Enhanced SiteMediaAsset with custom manager
SiteMediaAsset.add_to_class('objects', AssetManager())

class TextAssetManager(models.Manager):
    """
    Custom manager for SiteTextAsset with common query patterns.
    """
    
    def rich_text(self):
        """Return only rich text assets"""
        return self.filter(is_rich_text=True)
    
    def plain_text(self):
        """Return only plain text assets"""
        return self.filter(is_rich_text=False)

# Enhanced SiteTextAsset with custom manager
SiteTextAsset.add_to_class('objects', TextAssetManager())
