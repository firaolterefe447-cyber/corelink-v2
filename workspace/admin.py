"""
Workspace Admin Interface - Enterprise Edition
Features: Autocomplete relations, custom HTML badges, annotated analytics, and high-level UX.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count

from .models import (

    Team,
    TeamMembership,
    JoinRequest,
    PreferenceApplication,
    ConnectionRequest,
    CompanyMessageToAdmin,
    ChatMessage  # <-- 1. Added ChatMessage here
)

# ==============================================================================
# INLINES (Clean Relational Management)
# ==============================================================================

class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 0
    autocomplete_fields = ('user',)  # No more ugly UUIDs! Beautiful search box.
    readonly_fields = ('created_at',)
    fields = ('user', 'role', 'created_at')
    classes = ('collapse',)


class JoinRequestInline(admin.TabularInline):
    model = JoinRequest
    extra = 0
    autocomplete_fields = ('applicant',)
    readonly_fields = ('created_at',)
    fields = ('applicant', 'status', 'created_at')
    classes = ('collapse',)


# ==============================================================================
# MAIN ADMIN CLASSES
# ==============================================================================

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'team_type', 'leader', 'member_count_display',
        'status_badge', 'is_recruiting', 'view_live_page'
    )
    list_display_links = ('name',)
    list_editable = ('is_recruiting',)
    list_filter = ('status', 'team_type', 'is_recruiting', 'created_at')
    search_fields = ('name', 'slug', 'mission', 'leader__username', 'leader__email')

    # The UX Magic: Replaces messy text strings with a sleek search dropdown
    autocomplete_fields = ('leader',)
    radio_fields = {'status': admin.HORIZONTAL, 'team_type': admin.HORIZONTAL}
    readonly_fields = ('slug', 'created_at', 'updated_at')
    inlines = [TeamMembershipInline, JoinRequestInline]

    fieldsets = (
        ('🏢 Team Identity', {
            'fields': ('name', 'slug', 'team_type', 'leader')
        }),
        ('🎯 Content & Mission', {
            'fields': ('mission', 'roles_needed', 'telegram_link')
        }),
        ('⚙️ Admin Control Hub', {
            'fields': ('status', 'is_recruiting', 'admin_feedback'),
            'description': "Manage team visibility, recruitment, and internal feedback."
        }),
        ('🔒 System Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # --- ADVANCED UX: Custom UI & Analytics ---

    def get_queryset(self, request):
        """Optimized query to prevent server lag when loading member counts."""
        qs = super().get_queryset(request)
        qs = qs.annotate(_member_count=Count('memberships'))
        return qs

    def member_count_display(self, obj):
        return format_html(
            '<b style="color: #4f46e5;">{} Members</b>', obj._member_count
        )
    member_count_display.short_description = "Team Size"
    member_count_display.admin_order_field = '_member_count'

    def status_badge(self, obj):
        """Creates beautiful colored pill badges for statuses."""
        colors = {
            'PENDING': '#f59e0b',    # Amber
            'APPROVED': '#10b981',   # Green
            'REJECTED': '#ef4444',   # Red
            'ARCHIVED': '#6b7280',   # Gray
        }
        color = colors.get(obj.status, '#374151')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; '
            'border-radius: 20px; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def view_live_page(self, obj):
        """Creates a clickable action button in the list table."""
        if obj.slug:
            url = obj.get_absolute_url()
            return format_html(
                '<a href="{}" target="_blank" style="'
                'background-color: #2563eb; color: white; padding: 4px 12px; '
                'border-radius: 4px; text-decoration: none; font-weight: bold; '
                'font-size: 11px; transition: 0.2s;">'
                '🌍 View Live</a>', url
            )
        return "-"
    view_live_page.short_description = "Live Link"


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'team', 'role', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('user__username', 'user__email', 'team__name')
    autocomplete_fields = ('user', 'team') # Clean search dropdowns


@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ('applicant', 'team', 'status_badge', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('applicant__username', 'applicant__email', 'team__name')
    autocomplete_fields = ('applicant', 'team')
    radio_fields = {'status': admin.HORIZONTAL}

    def status_badge(self, obj):
        colors = {'PENDING': '#f59e0b', 'APPROVED': '#10b981', 'REJECTED': '#ef4444'}
        color = colors.get(obj.status, '#374151')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"


@admin.register(PreferenceApplication)
class PreferenceApplicationAdmin(admin.ModelAdmin):
    list_display = ('user', 'target_role_title', 'seeking', 'status_badge', 'created_at')
    list_filter = ('status', 'seeking', 'created_at')
    search_fields = ('user__username', 'user__email', 'target_role_title')
    autocomplete_fields = ('user',)
    radio_fields = {'status': admin.HORIZONTAL, 'seeking': admin.HORIZONTAL}

    fieldsets = (
        ('👤 Applicant', {
            'fields': ('user', 'target_role_title', 'seeking', 'preferred_location')
        }),
        ('📄 Profile Details', {
            'fields': ('ideal_company_desc', 'value_proposition')
        }),
        ('🎯 Admin Matchmaking', {
            'fields': ('status', 'admin_match_notes'),
        }),
    )

    def status_badge(self, obj):
        colors = {
            'SUBMITTED': '#3b82f6', 'VETTING': '#f59e0b',
            'HUNTING': '#8b5cf6', 'PLACED': '#10b981', 'ARCHIVED': '#6b7280'
        }
        color = colors.get(obj.status, '#374151')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; '
            'border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"




@admin.register(ConnectionRequest)
class ConnectionRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'assigned_connection', 'status_badge', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'user__username', 'assigned_connection__username')
    autocomplete_fields = ('user', 'assigned_connection')
    radio_fields = {'status': admin.HORIZONTAL}

    def status_badge(self, obj):
        colors = {
            'APPLIED': '#f59e0b', 'REVIEWING': '#3b82f6', 'MATCHING': '#8b5cf6',
            'CONNECTED': '#10b981', 'REJECTED': '#ef4444', 'CLOSED': '#6b7280'
        }
        color = colors.get(obj.status, '#374151')
        return format_html(
            '<span style="border: 1px solid {}; color: {}; padding: 3px 8px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            color, color, obj.get_status_display()
        )
    status_badge.short_description = "Status"


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
    list_display = ('sender', 'receiver', 'short_body', 'read_status_badge', 'timestamp')
    list_filter = ('is_read', 'timestamp')
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
            'fields': ('is_read',),
            'classes': ('collapse',)
        }),
    )

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