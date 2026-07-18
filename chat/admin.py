"""
Chat Admin Interface - Enterprise Edition
Features: Autocomplete relations, custom HTML badges, annotated analytics, and high-level UX.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count

from .models import (
    CompanyMessageToAdmin,
    ChatMessage
)

# ==============================================================================
# MAIN ADMIN CLASSES
# ==============================================================================

@admin.register(CompanyMessageToAdmin)
class CompanyMessageAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'founder', 'status_badge', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'company__name', 'founder__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    autocomplete_fields = ('company', 'founder', 'assigned_admin')
    radio_fields = {'status': admin.HORIZONTAL}

    fieldsets = (
        ('📩 The Request', {
            'fields': ('company', 'founder', 'title', 'description')
        }),
        ('🛠️ Admin Action Hub', {
            'fields': ('status', 'assigned_admin', 'admin_notes'),
            'description': "Founders do NOT see admin notes."
        }),
    )

    def status_badge(self, obj):
        colors = {'SUBMITTED': '#ef4444', 'REVIEWING': '#f59e0b', 'ACTIONING': '#3b82f6', 'RESOLVED': '#10b981', 'CLOSED': '#6b7280'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#000'), obj.get_status_display()
        )
    status_badge.short_description = "Status"


# ==============================================================================
# SECTION 4: COMMUNICATIONS / CHAT
# ==============================================================================

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'short_body', 'read_status_badge', 'delete_status_badge', 'timestamp')
    list_filter = ('is_read', 'is_deleted', 'timestamp')
    search_fields = ('sender__username', 'sender__email', 'receiver__username', 'receiver__email', 'body')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'

    # 2. Replaces standard dropdowns with searchable inputs (crucial for Users)
    autocomplete_fields = ('sender', 'receiver')

    # 3. Organizes the detail view beautifully
    fieldsets = (
        ('👥 Participants', {
            'fields': ('sender', 'receiver')
        }),
        ('💬 Message Content', {
            'fields': ('body',)
        }),
        ('⚙️ Metadata', {
            'fields': ('is_read', 'is_deleted'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Show all messages including soft-deleted ones for admin visibility."""
        qs = super().get_queryset(request)
        return qs

    def delete_model(self, request, obj):
        """Override to use soft delete instead of hard delete."""
        obj.is_deleted = True
        obj.save()

    def delete_queryset(self, request, queryset):
        """Override to use soft delete for bulk actions."""
        queryset.update(is_deleted=True)

    def delete_status_badge(self, obj):
        """Shows if message is soft-deleted."""
        if obj.is_deleted:
            return format_html('<span style="color: #ef4444; font-weight: bold;">🗑 Deleted</span>')
        return format_html('<span style="color: #10b981; font-weight: bold;">✓ Active</span>')
    delete_status_badge.short_description = "Status"

    def short_body(self, obj):
        """Truncates long messages for a cleaner table view."""
        if len(obj.body) > 65:
            return obj.body[:65] + '...'
        return obj.body
    short_body.short_description = 'Message Preview'

    def read_status_badge(self, obj):
        """Creates a visual indicator for read/unread messages."""
        if obj.is_read:
            return format_html('<span style="color: #10b981; font-weight: bold;">✓ Read</span>')
        return format_html('<span style="color: #f59e0b; font-weight: bold;">✉ Unread</span>')
    read_status_badge.short_description = "Status"