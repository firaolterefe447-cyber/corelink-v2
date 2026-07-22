"""
Service Admin Configuration
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.contrib.admin import ModelAdmin, TabularInline, StackedInline
from django.contrib.admin.decorators import display

from .models import Service, ServiceGallery


def get_admin_url(obj):
    """Get admin URL for an object."""
    from django.urls import reverse
    return reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', args=[obj.pk])


class ServiceGalleryInline(TabularInline):
    model = ServiceGallery
    extra = 1
    tab = True
    fields = ('image_preview', 'image', 'caption', 'order')
    readonly_fields = ('image_preview',)

    @display(description='Preview')
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" class="h-12 w-auto rounded border border-gray-200 shadow-sm" />', obj.image.url)
        return "-"


@admin.register(Service)
class ServiceAdmin(ModelAdmin):
    list_display = ('title', 'profile_link', 'is_active_badge', 'gallery_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'description', 'profile__user__email')
    autocomplete_fields = ['profile']
    inlines = [ServiceGalleryInline]

    fieldsets = (
        (None, {'fields': ('profile', 'title', 'description')}),
        ('Settings', {'fields': (('is_active', 'order'),)}),
    )

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)

    @display(description="Status")
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="bg-emerald-500 text-white px-2 py-1 rounded text-xs font-semibold">Active</span>')
        return format_html('<span class="bg-gray-400 text-white px-2 py-1 rounded text-xs font-semibold">Inactive</span>')

    @display(description="Images")
    def gallery_count(self, obj):
        return obj.gallery.count()


@admin.register(ServiceGallery)
class ServiceGalleryAdmin(ModelAdmin):
    list_display = ('service_link', 'image_preview', 'caption', 'order')
    list_filter = ('service',)
    search_fields = ('caption', 'service__title')
    autocomplete_fields = ['service']

    @display(description=_("Service"))
    def service_link(self, obj):
        url = get_admin_url(obj.service)
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, obj.service.title)

    @display(description='Preview')
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" class="h-12 w-auto rounded border border-gray-200 shadow-sm" />', obj.image.url)
        return "-"
