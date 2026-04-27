from django.contrib import admin
from .models import NewsArticle, NewsGalleryImage, NexusArticle, NexusGalleryImage

# --- 1. NEWS ADMINISTRATION ---

class NewsGalleryInline(admin.TabularInline):
    """Allows adding multiple images directly inside the News Article page."""
    model = NewsGalleryImage
    extra = 1
    fields = ('image', 'caption', 'order')

@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    inlines = [NewsGalleryInline]
    list_display = ('title', 'category', 'is_published', 'created_at', 'author_name')
    list_filter = ('is_published', 'category')
    search_fields = ('title', 'body', 'summary')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('-created_at',)
    list_per_page = 20

# --- 2. NEXUS (KNOWLEDGE BASE) ADMINISTRATION ---

class NexusGalleryInline(admin.TabularInline):
    model = NexusGalleryImage
    extra = 1

@admin.register(NexusArticle)
class NexusArticleAdmin(admin.ModelAdmin):
    inlines = [NexusGalleryInline]
    list_display = ('title', 'author', 'is_published', 'created_at')
    list_filter = ('is_published',)
    search_fields = ('title', 'content')