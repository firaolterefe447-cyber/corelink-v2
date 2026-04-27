"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CORELINK CONTENT MANAGEMENT SYSTEM                        ║
║                    Professional Content & Media Platform                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

Domain: Content Management & Publishing
Description: 
    Comprehensive content management system for news, articles, and knowledge base.
    Supports rich media, automatic optimization, and flexible publishing workflows.
    
Key Features:
    • News article management with categorization
    • Gallery support with image optimization
    • Knowledge base (Nexus) for user-generated content
    • Automatic image processing and WebP conversion
    • SEO-friendly slug generation
    • Flexible content publishing workflows

Architecture:
    - NewsArticle: Platform news and updates
    - NewsGalleryImage: News article gallery support
    - NexusArticle: User-generated knowledge base
    - NexusGalleryImage: Knowledge base gallery support

Author: CoreLink Development Team
Version: 2.0.0
Last Updated: 2024
"""

# ═══════════════════════════════════════════════════════════════════════════════
# # SYSTEM IMPORTS & DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════════════
import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

# ═══════════════════════════════════════════════════════════════════════════════
# # INTERNAL DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════════════
from core.models import TimeStampedModel
from core.services import optimize_cover_image

# ═══════════════════════════════════════════════════════════════════════════════
# # 1. NEWS & PLATFORM UPDATES
# ═══════════════════════════════════════════════════════════════════════════════

class NewsArticle(TimeStampedModel):
    """
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                    PLATFORM NEWS & UPDATES MANAGER                         ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    
    Purpose: Centralized management of platform news, insights, and community updates
    
    Features:
    • Multi-category content organization
    • Automatic SEO-friendly slug generation
    • Rich media support with cover images
    • Gallery integration for multiple images
    • Reading time estimation
    • Publication workflow control
    
    Content Types:
    - Platform Updates: System announcements
    - Community Events: Meetups and gatherings
    - Market Insights: Industry analysis
    - Member Spotlight: User achievements
    
    Performance:
    - Optimized image processing
    - Database indexing for fast queries
    - Efficient slug generation
    """

    class Category(models.TextChoices):
        """Content categorization system for news articles"""
        PLATFORM = 'PLATFORM', _('Platform Update')
        EVENT = 'EVENT', _('Community Event')
        INSIGHT = 'INSIGHT', _('Market Insight')
        SPOTLIGHT = 'SPOTLIGHT', _('Member Spotlight')

    # ═══════════════════════════════════════════════════════════════════════════════
    # # IDENTITY & METADATA
    # ═══════════════════════════════════════════════════════════════════════════════
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ═══════════════════════════════════════════════════════════════════════════════
    # # CONTENT FIELDS
    # ═══════════════════════════════════════════════════════════════════════════════
    title = models.CharField(
        max_length=255,
        help_text=_("Headline for the news article")
    )
    slug = models.SlugField(
        unique=True, 
        blank=True, 
        max_length=255,
        help_text=_("SEO-friendly URL. Auto-generated from title.")
    )
    category = models.CharField(
        max_length=20, 
        choices=Category.choices, 
        default=Category.PLATFORM,
        help_text=_("Content category for organization and filtering")
    )

    # ═══════════════════════════════════════════════════════════════════════════════
    # # MEDIA ASSETS
    # ═══════════════════════════════════════════════════════════════════════════════
    cover_image = models.ImageField(
        upload_to='content/news_covers/', 
        null=True, 
        blank=True,
        help_text=_("Primary cover image. Auto-optimized for web.")
    )

    # ═══════════════════════════════════════════════════════════════════════════════
    # # CONTENT BODY
    # ═══════════════════════════════════════════════════════════════════════════════
    summary = models.TextField(
        max_length=300, 
        help_text=_("Short teaser for the grid card and previews")
    )
    body = models.TextField(
        help_text=_("Full content. Supports HTML and Markdown formatting")
    )

    # ═══════════════════════════════════════════════════════════════════════════════
    # # PUBLISHING METADATA
    # ═══════════════════════════════════════════════════════════════════════════════
    author_name = models.CharField(
        max_length=100, 
        default="CoreLink Team",
        help_text=_("Display name for the content author")
    )
    is_published = models.BooleanField(
        default=True,
        help_text=_("Controls visibility on the platform")
    )
    read_time = models.IntegerField(
        default=5, 
        help_text=_("Estimated reading time in minutes")
    )

    class Meta:
        verbose_name = "News Article"
        verbose_name_plural = "News Articles"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'is_published']),
            models.Index(fields=['created_at']),
            models.Index(fields=['slug']),
        ]

    def save(self, *args, **kwargs):
        """
        Enhanced save method with automatic slug generation and image optimization.
        
        Features:
        - SEO-friendly slug generation with UUID suffix
        - Automatic image optimization to WebP format
        - Graceful error handling for media processing
        """
        # Generate unique slug if not provided
        if not self.slug:
            base_slug = slugify(self.title)
            unique_suffix = str(uuid.uuid4())[:4]
            self.slug = f"{base_slug}-{unique_suffix}"

        # Optimize cover image if present
        if self.cover_image:
            try:
                optimized = optimize_cover_image(self.cover_image)
                if optimized:
                    self.cover_image = optimized
            except Exception as e:
                # Log error but don't fail the save operation
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Image optimization failed for {self.slug}: {e}")

        super().save(*args, **kwargs)

    def __str__(self):
        """Human-readable representation"""
        return self.title

    def get_absolute_url(self):
        """Generate the absolute URL for this article"""
        from django.urls import reverse
        return reverse('news_detail', kwargs={'slug': self.slug})

class NewsGalleryImage(TimeStampedModel):
    """
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                    NEWS GALLERY IMAGE MANAGER                              ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    
    Purpose: Multi-image gallery support for news articles
    
    Features:
    • Ordered image display
    • Caption support for each image
    • Automatic image optimization
    • Foreign key relationship to NewsArticle
    
    Usage:
    - Photo essays
    - Event coverage
    - Product showcases
    - Tutorial illustrations
    """
    article = models.ForeignKey(
        NewsArticle,
        on_delete=models.CASCADE,
        related_name='gallery_images',
        help_text=_("Parent news article")
    )
    image = models.ImageField(
        upload_to='content/news_gallery/',
        help_text=_("Gallery image. Auto-optimized for web.")
    )
    caption = models.CharField(
        max_length=255, 
        blank=True,
        help_text=_("Optional caption for the image")
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text=_("Display order in the gallery")
    )

    class Meta:
        ordering = ['order']
        verbose_name = "Gallery Image"
        verbose_name_plural = "Gallery Images"
        indexes = [
            models.Index(fields=['article', 'order']),
        ]

    def save(self, *args, **kwargs):
        """
        Enhanced save with automatic image optimization.
        
        Features:
        - WebP conversion for better performance
        - Error handling for media processing
        """
        if self.image:
            try:
                optimized = optimize_cover_image(self.image)
                if optimized:
                    self.image = optimized
            except Exception as e:
                # Log error but don't fail the save operation
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Gallery image optimization failed: {e}")
        
        super().save(*args, **kwargs)

    def __str__(self):
        """Human-readable representation"""
        return f"Gallery image for {self.article.title}"

# ═══════════════════════════════════════════════════════════════════════════════
# # 2. NEXUS KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════════════════════════════

class NexusArticle(TimeStampedModel):
    """
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                    NEXUS KNOWLEDGE BASE MANAGER                            ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    
    Purpose: User-generated content and knowledge base system
    
    Features:
    • User-authored articles and tutorials
    • Rich content support with HTML/Markdown
    • Publication workflow control
    • Gallery integration for visual content
    • Author attribution system
    
    Use Cases:
    - Technical tutorials
    - Industry insights
    - Case studies
    - Best practices
    - Research findings
    
    Workflow:
    1. User creates content draft
    2. Admin reviews and publishes
    3. Content becomes visible in Nexus
    4. Community can engage with content
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='nexus_articles',
        help_text=_("Content author")
    )
    title = models.CharField(
        max_length=200,
        help_text=_("Article title for the knowledge base")
    )
    content = models.TextField(
        help_text=_("Full article content. Supports HTML and Markdown")
    )
    is_published = models.BooleanField(
        default=False,
        help_text=_("Controls visibility in the knowledge base")
    )

    class Meta:
        verbose_name = "Nexus Article"
        verbose_name_plural = "Nexus Articles"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['author', 'is_published']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        """Human-readable representation"""
        return self.title

    def get_absolute_url(self):
        """Generate the absolute URL for this article"""
        from django.urls import reverse
        return reverse('nexus_detail', kwargs={'pk': self.pk})

    @property
    def summary(self):
        """
        Generate a brief summary from the content.
        
        Returns:
            str: First 200 characters of content with ellipsis
        """
        return self.content[:200] + '...' if len(self.content) > 200 else self.content

class NexusGalleryImage(TimeStampedModel):
    """
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                    NEXUS GALLERY IMAGE MANAGER                             ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    
    Purpose: Image gallery support for Nexus knowledge base articles
    
    Features:
    • Visual content enhancement for articles
    • Caption support for context
    • Ordered display system
    • Public storage for accessibility
    
    Usage:
    - Tutorial screenshots
    - Diagrams and charts
    - Photo documentation
    - Visual examples
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nexus = models.ForeignKey(
        NexusArticle, 
        on_delete=models.CASCADE, 
        related_name='gallery',
        help_text=_("Parent Nexus article")
    )
    image = models.ImageField(
        upload_to='public/nexus/',
        help_text=_("Article image or diagram")
    )
    caption = models.CharField(
        max_length=200, 
        blank=True,
        help_text=_("Descriptive caption for the image")
    )

    class Meta:
        verbose_name = "Nexus Gallery Image"
        verbose_name_plural = "Nexus Gallery Images"
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['nexus', 'created_at']),
        ]

    def __str__(self):
        """Human-readable representation"""
        return f"Image for {self.nexus.title}"
