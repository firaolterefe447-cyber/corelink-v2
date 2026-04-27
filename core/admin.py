from django.contrib import admin
from .models import SiteMediaAsset, SiteTextAsset

@admin.register(SiteMediaAsset)
class SiteMediaAssetAdmin(admin.ModelAdmin):
    list_display = ('title', 'zone_slug', 'is_active', 'order')
    list_filter = ('zone_slug', 'is_active')
    search_fields = ('title', 'zone_slug')
    ordering = ('zone_slug', 'order')

@admin.register(SiteTextAsset)
class SiteTextAssetAdmin(admin.ModelAdmin):
    list_display = ('key', 'description', 'is_rich_text')
    search_fields = ('key', 'content')