"""
CORELINK UNIFIED PORTFOLIO & COMPANY SYSTEM - ADMIN DASHBOARD
Features Unfold framework integration, tabbed inlines, and Tailwind UI components.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

# Unfold Framework
from unfold.admin import ModelAdmin, TabularInline, StackedInline
from unfold.decorators import display
from unfold.contrib.filters.admin import (
    RangeNumericFilter,
)

# Domain Models
from .models import (
    # Unified Profile Cluster (New Architecture)
    UserProfile, ProfileHeadline, Skill, Credential,
    PortfolioProject, ProjectGallery, WorkExperience,
    ContentPost, UnifiedJobPreference, LiveOpportunity,

    # Right Now Ecosystem
    RightNowPost, RightNowMedia, RightNowLike, RightNowComment,

    # Company Cluster (Legacy)
    Company, CompanyMember, CompanyService, ServiceGalleryImage,
    CompanyMilestone, CompanyNews, NewsGalleryImage, CompanySocialLink, CompanyContactMethod
)

# ==============================================================================
# 0. UI HELPERS & DECORATORS
# ==============================================================================

def get_admin_url(obj):
    """Helper to generate admin URLs for related objects."""
    return reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', args=[obj.pk])

def star_rating(value):
    """Generates a visual star rating representation via Tailwind."""
    if value is None: return "-"
    stars = "⭐" * int(value)
    return format_html(
        '<span class="text-amber-500 text-lg">{}</span> <span class="text-gray-400 text-xs font-mono ml-1">({}/5)</span>',
        stars, value
    )

# ==============================================================================
# 1. UNIFIED PROFILE INLINES (THE LEGO BLOCKS)
# ==============================================================================

class ProfileHeadlineInline(TabularInline):
    model = ProfileHeadline
    extra = 0
    tab = True
    fields = ('title', 'is_primary', 'order')
    ordering = ('-is_primary', 'order')

class SkillInline(TabularInline):
    model = Skill
    extra = 0
    tab = True
    fields = ('name', 'status', 'proficiency_level', 'progress_bar', 'admin_status')
    readonly_fields = ('admin_status',)

class WorkExperienceInline(StackedInline):
    model = WorkExperience
    extra = 0
    tab = True
    fieldsets = (
        (None, {'fields': (('company_name', 'role_title'), ('start_date', 'end_date'), ('is_current', 'location_type'), 'description')}),
    )

class LiveOpportunityInline(TabularInline):
    model = LiveOpportunity
    extra = 0
    tab = True
    fields = ('request_type', 'title', 'expires_at', 'is_active', 'is_valid_badge')
    readonly_fields = ('is_valid_badge',)

    @display(description="Status")
    def is_valid_badge(self, obj):
        if obj.is_valid:
            return format_html('<span class="bg-emerald-500 text-white px-2 py-1 rounded-full text-[10px] font-bold tracking-wide">LIVE</span>')
        return format_html('<span class="bg-red-500 text-white px-2 py-1 rounded-full text-[10px] font-bold tracking-wide">EXPIRED</span>')

class UnifiedJobPreferenceInline(StackedInline):
    model = UnifiedJobPreference
    extra = 0
    tab = True
    fields = (('role_title', 'is_active'), ('work_arrangement', 'commitment_type'), 'description')

class ProjectGalleryInline(TabularInline):
    model = ProjectGallery
    extra = 1
    tab = True
    fields = ('image_preview', 'image', 'caption', 'order')
    readonly_fields = ('image_preview',)

    @display(description='Preview')
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" class="h-12 w-auto rounded border border-gray-200 shadow-sm" />', obj.image.url)
        return "-"

# ==============================================================================
# 2. RIGHT NOW ECOSYSTEM INLINES
# ==============================================================================

class RightNowMediaInline(TabularInline):
    model = RightNowMedia
    extra = 1
    tab = True
    fields = ('image_preview', 'image', 'order_index')
    readonly_fields = ('image_preview',)

    @display(description='Preview')
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" class="h-12 w-auto rounded border border-gray-200 shadow-sm" />', obj.image.url)
        return "-"

class RightNowCommentInline(TabularInline):
    model = RightNowComment
    extra = 0
    tab = True
    autocomplete_fields = ['author']
    fields = ('author', 'body', 'created_at')
    readonly_fields = ('created_at',)

class RightNowLikeInline(TabularInline):
    model = RightNowLike
    extra = 0
    tab = True
    autocomplete_fields = ['profile']
    fields = ('profile', 'created_at')
    readonly_fields = ('created_at',)


# ==============================================================================
# 3. COMPANY INLINES (UNCHANGED)
# ==============================================================================

class CompanySocialLinkInline(TabularInline):
    model = CompanySocialLink
    extra = 1
    tab = True

class CompanyContactMethodInline(TabularInline):
    model = CompanyContactMethod
    extra = 1
    tab = True

class CompanyMilestoneInline(TabularInline):
    model = CompanyMilestone
    extra = 0
    tab = True
    ordering = ('-year',)

class CompanyMemberInline(TabularInline):
    model = CompanyMember
    extra = 0
    tab = True
    autocomplete_fields = ['user']
    fields = ('user', 'role', 'job_title', 'is_active')

class ServiceGalleryImageInline(TabularInline):
    model = ServiceGalleryImage
    extra = 1
    tab = True

class NewsGalleryImageInline(TabularInline):
    model = NewsGalleryImage
    extra = 1
    tab = True


# ==============================================================================
# 4. THE LOBBY: UNIFIED PROFILE ADMIN
# ==============================================================================

@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = (
        'user_identity', 'collaboration_badge', 'search_intent_badge',
        'rating_display', 'last_signal_update'
    )
    list_filter = (
        'collaboration_status', 'current_search', 'is_rating_locked',
        ('admin_rating', RangeNumericFilter)
    )
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'slug', 'location', 'institution')
    readonly_fields = ('slug', 'last_signal_update', 'created_at', 'updated_at')
    autocomplete_fields = ['user']

    inlines = [
        ProfileHeadlineInline,
        SkillInline,
        WorkExperienceInline,
        UnifiedJobPreferenceInline,
        LiveOpportunityInline
    ]

    fieldsets = (
        (_('👑 Core Identity'), {
            'fields': (('user', 'slug'), 'cv_file'),
            "classes": ("tab-content",),
        }),
        (_('📡 Real-Time Intent'), {
            'fields': (('current_search', 'collaboration_status'), 'current_mission'),
            "classes": ("tab-content", "bg-gray-50"),
        }),
        (_('📜 Professional Narrative'), {
            'fields': ('bio_narrative',),
            "classes": ("tab-content",),
        }),
        (_('⚠️ Legacy Data Preservations'), {
            'fields': (('location', 'institution'), ('field_of_interest', 'years_experience')),
            "classes": ("collapse", "bg-amber-50"),
        }),
        (_('⭐ System & Scoring'), {
            'fields': (('admin_rating', 'is_rating_locked'), 'last_signal_update', ('created_at', 'updated_at')),
            "classes": ("collapse",),
        }),
    )

    actions = ['lock_ratings', 'unlock_ratings', 'boost_rating']

    @display(description=_("User Identity"), ordering='user__last_name')
    def user_identity(self, obj):
        name = getattr(obj.user, 'full_name', str(obj.user))
        return format_html(
            '<div class="font-semibold text-gray-900">{}</div><div class="text-xs text-gray-500 font-mono">{}</div>',
            name, obj.slug
        )

    @display(description=_("Availability"), ordering='collaboration_status')
    def collaboration_badge(self, obj):
        colors = {
            'OPEN': 'bg-emerald-500',
            'CASUAL': 'bg-blue-500',
            'CLOSED': 'bg-gray-500'
        }
        bg_color = colors.get(obj.collaboration_status, 'bg-gray-500')
        return format_html(
            '<span class="{} text-white px-2 py-1 rounded text-xs font-semibold">{}</span>',
            bg_color,
            obj.get_collaboration_status_display()
        )

    @display(description=_("Intent"), ordering='current_search')
    def search_intent_badge(self, obj):
        return format_html(
            '<span class="border border-indigo-500 text-indigo-600 bg-indigo-50 px-2 py-1 rounded text-xs font-medium">{}</span>',
            obj.get_current_search_display()
        )

    @display(description=_("Rating"), ordering='admin_rating')
    def rating_display(self, obj):
        lock_icon = " 🔒" if obj.is_rating_locked else ""
        return format_html('{} <span class="text-xs">{}</span>', star_rating(obj.admin_rating), lock_icon)

    @admin.action(description="Lock ratings for selected profiles")
    def lock_ratings(self, request, queryset):
        queryset.update(is_rating_locked=True)

    @admin.action(description="Unlock ratings for selected profiles")
    def unlock_ratings(self, request, queryset):
        queryset.update(is_rating_locked=False)

    @admin.action(description="Boost Platform Rating (+1) safely")
    def boost_rating(self, request, queryset):
        for profile in queryset.filter(is_rating_locked=False, admin_rating__lt=5):
            profile.admin_rating += 1
            profile.save(update_fields=['admin_rating'])


# ==============================================================================
# 5. "RIGHT NOW" ECOSYSTEM ADMIN (NEW)
# ==============================================================================

# ==============================================================================
# 5. "RIGHT NOW" ECOSYSTEM ADMIN (NEW)
# ==============================================================================

@admin.register(RightNowPost)
class RightNowPostAdmin(ModelAdmin):
    list_display = ('profile', 'short_title', 'engagement_metrics', 'is_active_focus', 'is_published', 'created_at')
    list_filter = ('is_published', 'is_active_focus', 'current_search', 'collaboration_status', 'created_at')
    search_fields = ('profile__user__email', 'profile__user__full_name', 'title', 'body_narrative', 'external_link')
    autocomplete_fields = ['profile']

    inlines = [RightNowMediaInline, RightNowCommentInline, RightNowLikeInline]

    fieldsets = (
        (_("Author & Networking Intent"), {
            "fields": ("profile", ("current_search", "collaboration_status")),
            "classes": ("tab-content",)
        }),
        (_("The Content (Post Details)"), {
            "fields": ("title", "body_narrative"),
            "classes": ("tab-content",),
            "description": "The main explanation/markdown text that users type."
        }),
        (_("External Link & Rich Preview Data"), {
            "fields": ("external_link", "link_title", "link_description", "link_image_url", "link_domain"),
            "classes": ("tab-content", "bg-blue-50"),
            "description": "If the user attaches a link, these fields auto-fill. You can manually edit the preview text here."
        }),
        (_("Denormalized Metrics (Engagement)"), {
            "fields": (("views_count", "clicks_count"), ("likes_count", "comments_count")),
            "classes": ("tab-content", "bg-amber-50"),
            "description": "Warning: These update automatically, but admins can manually force an adjustment."
        }),
        (_("State & Visibility"), {
            "fields": (("is_published", "is_active_focus"),),
            "classes": ("tab-content",)
        })
    )

    @display(description="Title", ordering="title")
    def short_title(self, obj):
        return obj.title if obj.title else format_html('<span class="text-gray-400 italic">No Title</span>')

    @display(description="Engagement Stats")
    def engagement_metrics(self, obj):
        return format_html(
            '<span class="text-xs font-semibold px-2 py-1 bg-gray-100 rounded text-gray-700 mr-1">❤️ {}</span>'
            '<span class="text-xs font-semibold px-2 py-1 bg-gray-100 rounded text-gray-700 mr-1">💬 {}</span>'
            '<span class="text-xs font-semibold px-2 py-1 bg-gray-100 rounded text-gray-700">👁️ {}</span>',
            obj.likes_count, obj.comments_count, obj.views_count
        )


@admin.register(RightNowComment)
class RightNowCommentAdmin(ModelAdmin):
    list_display = ('author', 'post_link', 'short_body', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('body', 'author__user__email', 'author__user__full_name')
    autocomplete_fields = ['post', 'author']

    @display(description="Post")
    def post_link(self, obj):
        url = get_admin_url(obj.post)
        return format_html('<a href="{}" class="text-blue-600 font-medium">View Post</a>', url)

    @display(description="Comment")
    def short_body(self, obj):
        return obj.body[:60] + "..." if len(obj.body) > 60 else obj.body


@admin.register(RightNowLike)
class RightNowLikeAdmin(ModelAdmin):
    list_display = ('profile', 'post_link', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('profile__user__email', 'profile__user__full_name')
    autocomplete_fields = ['post', 'profile']

    @display(description="Post")
    def post_link(self, obj):
        url = get_admin_url(obj.post)
        return format_html('<a href="{}" class="text-blue-600 font-medium">View Post</a>', url)

class RightNowCommentAdmin(ModelAdmin):
    list_display = ('author', 'post_link', 'short_body', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('body', 'author__user__email', 'author__user__full_name')
    autocomplete_fields = ['post', 'author']

    @display(description="Post")
    def post_link(self, obj):
        url = get_admin_url(obj.post)
        return format_html('<a href="{}" class="text-blue-600 font-medium">View Post</a>', url)

    @display(description="Comment")
    def short_body(self, obj):
        return obj.body[:60] + "..." if len(obj.body) > 60 else obj.body


class RightNowLikeAdmin(ModelAdmin):
    list_display = ('profile', 'post_link', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('profile__user__email', 'profile__user__full_name')
    autocomplete_fields = ['post', 'profile']

    @display(description="Post")
    def post_link(self, obj):
        url = get_admin_url(obj.post)
        return format_html('<a href="{}" class="text-blue-600 font-medium">View Post</a>', url)


# ==============================================================================
# 6. MODULAR ASSET ADMINS (PROJECTS, POSTS, CREDENTIALS)
# ==============================================================================

@admin.register(PortfolioProject)
class PortfolioProjectAdmin(ModelAdmin):
    list_display = ('title', 'profile_link', 'context', 'has_link', 'created_at')
    list_filter = ('context',)
    search_fields = ('title', 'client_name', 'profile__user__email')
    autocomplete_fields = ['profile']
    inlines = [ProjectGalleryInline]

    fieldsets = (
        (None, {'fields': ('profile', 'title', 'context', 'order')}),
        ('Details', {'fields': (('role', 'client_name'), 'problem_statement', 'solution_narrative', 'main_description')}),
        ('Links', {'fields': ('link',)})
    )

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)

    @display(boolean=True, description='Live Link')
    def has_link(self, obj):
        return bool(obj.link)

@admin.register(ContentPost)
class ContentPostAdmin(ModelAdmin):
    list_display = ('title', 'profile', 'post_type', 'visibility', 'is_verified', 'created_at')
    list_filter = ('post_type', 'visibility', 'is_verified', 'created_at')
    search_fields = ('title', 'content', 'profile__user__email')
    autocomplete_fields = ['profile']
    actions = ['verify_posts']

    fieldsets = (
        (None, {'fields': ('profile', 'post_type', 'category', 'title')}),
        ('Content', {'fields': ('content', 'media_proof')}),
        ('Settings', {'fields': (('visibility', 'is_verified'), 'order')}),
    )

    @admin.action(description="Verify selected content posts")
    def verify_posts(self, request, queryset):
        queryset.update(is_verified=True)

@admin.register(Credential)
class CredentialAdmin(ModelAdmin):
    list_display = ('title', 'profile', 'issuer', 'credential_type', 'issue_date', 'verification_status')
    list_filter = ('is_admin_verified', 'credential_type', 'issue_date')
    search_fields = ('title', 'issuer', 'profile__user__email')
    autocomplete_fields = ['profile']
    actions = ['verify_credentials']

    @display(description='Status')
    def verification_status(self, obj):
        if obj.is_admin_verified:
            return format_html('<span class="text-emerald-600 font-bold">✔ Verified</span>')
        return format_html('<span class="text-amber-500 font-bold">⏱ Pending</span>')

    @admin.action(description="Mark selected as Admin Verified")
    def verify_credentials(self, request, queryset):
        queryset.update(is_admin_verified=True)

@admin.register(LiveOpportunity)
class LiveOpportunityAdmin(ModelAdmin):
    list_display = ('title', 'profile', 'request_type', 'expires_at', 'status_badge')
    list_filter = ('request_type', 'is_active')
    search_fields = ('title', 'details', 'profile__user__email')
    autocomplete_fields = ['profile']

    @display(description="Network Status")
    def status_badge(self, obj):
        if not obj.is_active:
            return format_html('<span class="text-red-500 font-semibold">Canceled</span>')

        if obj.expires_at is None or obj.expires_at > timezone.now():
            return format_html('<span class="text-emerald-500 font-bold">🟢 Broadcasting</span>')

        return format_html('<span class="text-gray-400 font-semibold">⏏ Expired</span>')

# ==============================================================================
# 7. COMPANY SYSTEM ADMINS (UNCHANGED)
# ==============================================================================

@admin.register(Company)
class CompanyAdmin(ModelAdmin):
    list_display = ('brand_identity', 'sector_badge', 'location', 'looking_for', 'is_hiring', 'operating_since')
    list_filter = ('is_hiring', 'looking_for', 'sector', 'operating_since')
    search_fields = ('name', 'slug', 'mission_stmt')
    readonly_fields = ('slug', 'created_at', 'updated_at')
    list_editable = ('is_hiring', 'looking_for')

    fieldsets = (
        (_("🏢 Corporate Headquarters"), {
            "fields": (("name", "slug"), ("sector", "operating_since"), "location"),
        }),
        (_("🎨 Brand Assets"), {
            "fields": (("logo", "cover_image"), "mission_stmt"),
        }),
        (_("🎯 Objectives & Hiring"), {
            "fields": (("looking_for", "is_hiring"),),
        }),
    )

    inlines = [
        CompanyContactMethodInline,
        CompanySocialLinkInline,
        CompanyMemberInline,
        CompanyMilestoneInline,
    ]

    @display(description=_("Company"), ordering='name')
    def brand_identity(self, obj):
        if obj.logo:
            return format_html(
                '<div class="flex items-center"><img src="{}" class="w-8 h-8 rounded object-cover mr-2 shadow-sm"><span class="font-semibold text-gray-900">{}</span></div>',
                obj.logo.url, obj.name
            )
        return format_html(
            '<div class="flex items-center"><span class="font-semibold text-gray-900">{}</span></div>',
            obj.name
        )

    @display(description=_("Sector"), ordering='sector')
    def sector_badge(self, obj):
        return format_html('<span class="bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs font-medium border border-gray-200">{}</span>', obj.sector)

@admin.register(CompanyNews)
class CompanyNewsAdmin(ModelAdmin):
    list_display = ('title', 'company', 'is_published', 'published_date')
    list_filter = ('is_published', 'published_date', 'company')
    search_fields = ('title', 'content', 'company__name')
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ['company']
    inlines = [NewsGalleryImageInline]

    fieldsets = (
        (None, {"fields": ("company", "title", "slug")}),
        (_("Content Body"), {"fields": ("cover_image", "excerpt", "content")}),
        (_("Publishing Control"), {"fields": (("is_published", "published_date"),)})
    )

@admin.register(CompanyService)
class CompanyServiceAdmin(ModelAdmin):
    list_display = ('name', 'company', 'is_active', 'order')
    list_filter = ('is_active', 'company')
    search_fields = ('name', 'description')
    autocomplete_fields = ['company']
    inlines = [ServiceGalleryImageInline]

@admin.register(CompanyMember)
class CompanyMemberAdmin(ModelAdmin):
    list_display = ('user', 'company', 'role', 'job_title', 'is_active')
    list_filter = ('role', 'is_active', 'company')
    search_fields = ('user__full_name', 'user__email', 'company__name')
    autocomplete_fields = ['user', 'company']
    list_editable = ('is_active', 'role')

# ==============================================================================
# 8. REGULAR MODELS
# ==============================================================================
admin.site.register(Skill)
