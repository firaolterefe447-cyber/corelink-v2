"""
CORELINK UNIFIED PORTFOLIO & COMPANY SYSTEM - ADMIN DASHBOARD
Features Unfold framework integration, tabbed inlines, and Tailwind UI components.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.safestring import mark_safe
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
    ContentPost, UnifiedJobPreference, LiveOpportunity, Language,

    # Right Now Ecosystem
    RightNowPost, RightNowMedia, RightNowLike, RightNowComment,

    # Company Cluster (Legacy)
    Company, CompanyMember, CompanyService, ServiceGalleryImage,
    CompanyMilestone, CompanyNews, NewsGalleryImage, CompanySocialLink, CompanyContactMethod,

    # Expert Profile Cluster
    ExpertProfile, ExpertHeadline, ExpertSkill, ExpertCredential,
    ExpertProject, ProjectGalleryImage, ExpertExperience, JobPreference, ExpertThought,

    # Visionary Profile Cluster
    VisionaryProfile, Certification, Project, ProjectImage,
    GrowthLog, LearningTarget, VisionBlock,

    # Founder Profile Cluster
    FounderProfile
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

    actions = ['lock_ratings', 'unlock_ratings', 'boost_rating', 'open_curation_interface']

    @admin.action(description="Open Feed Curation Interface")
    def open_curation_interface(self, request, queryset):
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        return HttpResponseRedirect(reverse('admin_curation'))

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
    list_display = ('profile', 'short_title', 'is_admin_selected_badge', 'is_active_focus', 'is_published', 'created_at')
    list_filter = ('is_published', 'is_active_focus', 'is_admin_selected', 'current_search', 'collaboration_status', 'created_at')
    search_fields = ('profile__user__email', 'profile__user__full_name', 'title', 'body_narrative', 'external_link')
    autocomplete_fields = ['profile']

    inlines = [RightNowMediaInline, RightNowCommentInline, RightNowLikeInline]

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['curation_url'] = reverse('admin_curation')
        return super().changelist_view(request, extra_context)

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

    @display(description="Feed Status")
    def is_admin_selected_badge(self, obj):
        if obj.is_admin_selected:
            return format_html('<span class="bg-purple-600 text-white px-2 py-1 rounded text-xs font-bold">✓ Selected</span>')
        return format_html('<span class="bg-gray-200 text-gray-600 px-2 py-1 rounded text-xs font-medium">Not Selected</span>')


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

# ==============================================================================
# 7. COMPANY SYSTEM ADMINS
# ==============================================================================
# ==============================================================================
# 7. COMPANY SYSTEM ADMINS
# ==============================================================================

# ==============================================================================
# 7. COMPANY SYSTEM ADMINS
# ==============================================================================

@admin.register(Company)
class CompanyAdmin(ModelAdmin):
    list_display = (
        'brand_identity', 'sector_badge', 'location',
        'is_selected', 'is_banned_from_nexus',
        'is_hiring'
    )

    list_filter = (
        'is_banned_from_nexus', 'is_selected',
        'is_hiring', 'looking_for', 'sector', 'operating_since'
    )

    search_fields = ('name', 'slug', 'mission_stmt')
    readonly_fields = ('slug', 'created_at', 'updated_at')

    list_editable = (
        'is_selected', 'is_banned_from_nexus',
        'is_hiring'
    )

    fieldsets = (
        (_("🏢 Corporate Headquarters"), {
            "fields": (("name", "slug"), ("sector", "operating_since"), "location"),
            "classes": ("tab-content",)
        }),
        (_("🎨 Brand Assets"), {
            "fields": (("logo", "cover_image"), "mission_stmt"),
            "classes": ("tab-content",)
        }),
        (_("🎯 Objectives & Hiring"), {
            "fields": (("looking_for", "is_hiring"),),
            "classes": ("tab-content",)
        }),
        (_("🛡️ Feed Control & Moderation"), {
            "fields": (
                'is_selected',
                'is_banned_from_nexus'
            ),
            "description": "Toggle visibility and pinning inside the public Company Nexus directory.",
            "classes": ("collapse", "bg-red-50")
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
        # 1. Fetch the correct Public Profile URL
        try:
            profile_url = obj.get_absolute_url()
        except Exception:
            profile_url = f"/company/{obj.slug}/"

        # 2. Sleek, professional View Profile link with SVG icon
        link_html = f'''
            <div style="margin-top: 6px;">
                <a href="{profile_url}" target="_blank" onclick="event.stopPropagation();" 
                   style="display: inline-flex; align-items: center; gap: 3px; font-size: 10px; font-weight: 600; color: #4338ca; text-decoration: none; text-transform: uppercase; letter-spacing: 0.5px;">
                    View Profile 
                    <svg width="10" height="10" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M7 17l9.2-9.2M17 17V7H7"/>
                    </svg>
                </a>
            </div>
        '''

        # 3. Fallback Logo if none exists
        logo_url = obj.logo.url if obj.logo else f"https://ui-avatars.com/api/?name={obj.name}&background=EBF4FF&color=7F9CF5"

        return format_html(
            '''
            <div style="display: flex; align-items: flex-start; gap: 10px; min-width: 180px;">
                <img src="{}" style="width: 36px; height: 36px; border-radius: 6px; object-fit: cover; border: 1px solid #eee; flex-shrink: 0;" />
                <div style="display: flex; flex-direction: column; overflow: hidden;">
                    <span style="font-weight: 600; font-size: 13px; line-height: 1.2;">{}</span>
                    {}
                </div>
            </div>
            ''',
            logo_url, obj.name, mark_safe(link_html)
        )

    @display(description=_("Sector"), ordering='sector')
    def sector_badge(self, obj):
        return format_html(
            '<span class="bg-gray-100 text-gray-700 px-2 py-1 rounded text-xs font-medium border border-gray-200">{}</span>',
            obj.sector)
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

@admin.register(Skill)
class SkillAdmin(ModelAdmin):
    list_display = ('name', 'profile_link', 'status', 'proficiency_level', 'progress_bar', 'admin_status')
    list_filter = ('status', 'proficiency_level', 'admin_status')
    search_fields = ('name', 'context', 'profile__user__email', 'profile__user__first_name', 'profile__user__last_name')
    autocomplete_fields = ['profile']

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)


@admin.register(WorkExperience)
class WorkExperienceAdmin(ModelAdmin):
    list_display = ('profile_link', 'company_name', 'role_title', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current', 'location_type', 'employment_type', 'start_date')
    search_fields = ('company_name', 'role_title', 'profile__user__email', 'profile__user__first_name', 'profile__user__last_name')
    autocomplete_fields = ['profile']

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)


@admin.register(Language)
class LanguageAdmin(ModelAdmin):
    list_display = ('profile_link', 'language_display', 'proficiency', 'is_primary')
    list_filter = ('proficiency', 'is_primary', 'language_code')
    search_fields = ('custom_language_name', 'profile__user__email', 'profile__user__first_name', 'profile__user__last_name')
    autocomplete_fields = ['profile']

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)

    @display(description=_("Language"))
    def language_display(self, obj):
        return obj.get_language_display()


@admin.register(ProfileHeadline)
class ProfileHeadlineAdmin(ModelAdmin):
    list_display = ('profile_link', 'title', 'is_primary', 'order')
    list_filter = ('is_primary',)
    search_fields = ('title', 'profile__user__email', 'profile__user__first_name', 'profile__user__last_name')
    autocomplete_fields = ['profile']

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)


@admin.register(UnifiedJobPreference)
class UnifiedJobPreferenceAdmin(ModelAdmin):
    list_display = ('profile_link', 'role_title', 'work_arrangement', 'commitment_type', 'is_active')
    list_filter = ('is_active', 'work_arrangement', 'commitment_type')
    search_fields = ('role_title', 'description', 'profile__user__email', 'profile__user__first_name', 'profile__user__last_name')
    autocomplete_fields = ['profile']

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)


@admin.register(ProjectGallery)
class ProjectGalleryAdmin(ModelAdmin):
    list_display = ('project_link', 'asset_type', 'caption', 'order')
    list_filter = ('asset_type',)
    search_fields = ('caption', 'project__title')
    autocomplete_fields = ['project']

    @display(description=_("Project"))
    def project_link(self, obj):
        url = get_admin_url(obj.project)
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, obj.project.title)


@admin.register(RightNowMedia)
class RightNowMediaAdmin(ModelAdmin):
    list_display = ('post_link', 'image_preview', 'order_index')
    search_fields = ('post__title', 'post__profile__user__email')
    autocomplete_fields = ['post']

    @display(description=_("Post"))
    def post_link(self, obj):
        url = get_admin_url(obj.post)
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, obj.post.title)

    @display(description='Preview')
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" class="h-12 w-auto rounded border border-gray-200 shadow-sm" />', obj.image.url)
        return "-"


# ==============================================================================
# 9. EXPERT PROFILE CLUSTER ADMINS
# ==============================================================================

@admin.register(ExpertProfile)
class ExpertProfileAdmin(ModelAdmin):
    list_display = ('user_identity', 'location', 'current_search', 'collaboration_status', 'rating_display', 'last_signal_update')
    list_filter = ('collaboration_status', 'current_search', 'is_rating_locked', ('admin_rating', RangeNumericFilter))
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'slug', 'location', 'bio_narrative')
    readonly_fields = ('slug', 'last_signal_update', 'created_at', 'updated_at')
    autocomplete_fields = ['user']

    fieldsets = (
        (_('👑 Core Identity'), {
            'fields': (('user', 'slug'), 'cv_file'),
            "classes": ("tab-content",),
        }),
        (_('📡 Real-Time Intent'), {
            'fields': (('current_search', 'collaboration_status'), 'right_now'),
            "classes": ("tab-content", "bg-gray-50"),
        }),
        (_('📜 Professional Narrative'), {
            'fields': ('bio_narrative', 'years_experience'),
            "classes": ("tab-content",),
        }),
        (_('⭐ System & Scoring'), {
            'fields': (('admin_rating', 'is_rating_locked'), 'last_signal_update', ('created_at', 'updated_at')),
            "classes": ("collapse",),
        }),
    )

    @display(description=_("User Identity"), ordering='user__last_name')
    def user_identity(self, obj):
        name = getattr(obj.user, 'full_name', str(obj.user))
        return format_html(
            '<div class="font-semibold text-gray-900">{}</div><div class="text-xs text-gray-500 font-mono">{}</div>',
            name, obj.slug or 'No slug'
        )

    @display(description=_("Rating"), ordering='admin_rating')
    def rating_display(self, obj):
        lock_icon = " 🔒" if obj.is_rating_locked else ""
        return format_html('{} <span class="text-xs">{}</span>', star_rating(obj.admin_rating), lock_icon)


@admin.register(ExpertSkill)
class ExpertSkillAdmin(ModelAdmin):
    list_display = ('profile_link', 'name', 'level', 'admin_status')
    list_filter = ('level', 'admin_status')
    search_fields = ('name', 'description', 'profile__user__email', 'profile__user__first_name', 'profile__user__last_name')
    autocomplete_fields = ['profile']

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)


@admin.register(ExpertCredential)
class ExpertCredentialAdmin(ModelAdmin):
    list_display = ('profile_link', 'degree_title', 'institution', 'year', 'admin_status')
    list_filter = ('year', 'admin_status')
    search_fields = ('degree_title', 'institution', 'profile__user__email', 'profile__user__first_name', 'profile__user__last_name')
    autocomplete_fields = ['profile']

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)


@admin.register(ExpertProject)
class ExpertProjectAdmin(ModelAdmin):
    list_display = ('profile_link', 'title', 'client_name', 'role', 'order')
    list_filter = ('order',)
    search_fields = ('title', 'client_name', 'role', 'profile__user__email', 'profile__user__first_name', 'profile__user__last_name')
    autocomplete_fields = ['profile']

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)


@admin.register(ExpertExperience)
class ExpertExperienceAdmin(ModelAdmin):
    list_display = ('profile_link', 'company_name', 'role_title', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current', 'location_type', 'start_date')
    search_fields = ('company_name', 'role_title', 'profile__user__email', 'profile__user__first_name', 'profile__user__last_name')
    autocomplete_fields = ['profile']

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)


@admin.register(ExpertThought)
class ExpertThoughtAdmin(ModelAdmin):
    list_display = ('profile_link', 'title', 'visibility', 'created_at')
    list_filter = ('visibility', 'created_at')
    search_fields = ('title', 'content', 'profile__user__email', 'profile__user__first_name', 'profile__user__last_name')
    autocomplete_fields = ['profile']

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)


@admin.register(JobPreference)
class JobPreferenceAdmin(ModelAdmin):
    list_display = ('expert_link', 'role_title', 'work_arrangement', 'commitment_type', 'is_active')
    list_filter = ('is_active', 'work_arrangement', 'commitment_type')
    search_fields = ('role_title', 'description', 'expert__user__email', 'expert__user__first_name', 'expert__user__last_name')
    autocomplete_fields = ['expert']

    @display(description=_("Expert"))
    def expert_link(self, obj):
        url = get_admin_url(obj.expert)
        name = getattr(obj.expert.user, 'full_name', str(obj.expert.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)


# ==============================================================================
# 10. VISIONARY PROFILE CLUSTER ADMINS
# ==============================================================================

@admin.register(VisionaryProfile)
class VisionaryProfileAdmin(ModelAdmin):
    list_display = ('user_identity', 'institution', 'field_of_interest', 'current_search', 'collaboration_status', 'rating_display', 'last_signal_update')
    list_filter = ('collaboration_status', 'current_search', 'is_rating_locked', 'field_of_interest', ('admin_rating', RangeNumericFilter))
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'slug', 'location', 'institution', 'bio_narrative')
    readonly_fields = ('slug', 'last_signal_update', 'created_at', 'updated_at')
    autocomplete_fields = ['user']

    fieldsets = (
        (_('👑 Core Identity'), {
            'fields': (('user', 'slug'), ('institution', 'location')),
            "classes": ("tab-content",),
        }),
        (_('📡 Real-Time Intent'), {
            'fields': (('current_search', 'collaboration_status'), 'right_now'),
            "classes": ("tab-content", "bg-gray-50"),
        }),
        (_('📜 Professional Narrative'), {
            'fields': (('current_title', 'field_of_interest'), 'bio_narrative', 'headline'),
            "classes": ("tab-content",),
        }),
        (_('⭐ System & Scoring'), {
            'fields': (('admin_rating', 'is_rating_locked'), 'last_signal_update', ('created_at', 'updated_at')),
            "classes": ("collapse",),
        }),
    )

    @display(description=_("User Identity"), ordering='user__last_name')
    def user_identity(self, obj):
        name = getattr(obj.user, 'full_name', str(obj.user))
        return format_html(
            '<div class="font-semibold text-gray-900">{}</div><div class="text-xs text-gray-500 font-mono">{}</div>',
            name, obj.slug or 'No slug'
        )

    @display(description=_("Rating"), ordering='admin_rating')
    def rating_display(self, obj):
        lock_icon = " 🔒" if obj.is_rating_locked else ""
        return format_html('{} <span class="text-xs">{}</span>', star_rating(obj.admin_rating), lock_icon)


@admin.register(Certification)
class CertificationAdmin(ModelAdmin):
    list_display = ('profile_link', 'name', 'issuing_organization', 'issue_date')
    list_filter = ('issue_date',)
    search_fields = ('name', 'issuing_organization', 'profile__user__email', 'profile__user__first_name', 'profile__user__last_name')
    autocomplete_fields = ['profile']

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)


@admin.register(Project)
class VisionaryProjectAdmin(ModelAdmin):
    list_display = ('profile_link', 'name', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'problem', 'solution', 'profile__user__email', 'profile__user__first_name', 'profile__user__last_name')
    autocomplete_fields = ['profile']

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)


@admin.register(GrowthLog)
class GrowthLogAdmin(ModelAdmin):
    list_display = ('profile_link', 'date', 'category', 'title', 'is_verified')
    list_filter = ('category', 'date', 'is_verified')
    search_fields = ('title', 'narrative', 'profile__user__email', 'profile__user__first_name', 'profile__user__last_name')
    autocomplete_fields = ['profile']

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)


@admin.register(LearningTarget)
class LearningTargetAdmin(ModelAdmin):
    list_display = ('profile_link', 'skill_name', 'status', 'progress_bar')
    list_filter = ('status',)
    search_fields = ('skill_name', 'learning_motivation', 'profile__user__email', 'profile__user__first_name', 'profile__user__last_name')
    autocomplete_fields = ['profile']

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)


@admin.register(VisionBlock)
class VisionBlockAdmin(ModelAdmin):
    list_display = ('profile_link', 'title', 'order')
    list_filter = ('order',)
    search_fields = ('title', 'content', 'profile__user__email', 'profile__user__first_name', 'profile__user__last_name')
    autocomplete_fields = ['profile']

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)


# ==============================================================================
# 11. FOUNDER PROFILE CLUSTER ADMINS
# ==============================================================================

@admin.register(FounderProfile)
class FounderProfileAdmin(ModelAdmin):
    list_display = ('user_identity', 'company_name', 'sector', 'current_search', 'collaboration_status', 'rating_display', 'last_signal_update')
    list_filter = ('collaboration_status', 'current_search', 'is_rating_locked', 'sector', ('admin_rating', RangeNumericFilter))
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'slug', 'company_name', 'mission_stmt')
    readonly_fields = ('slug', 'last_signal_update', 'created_at', 'updated_at')
    autocomplete_fields = ['user']

    fieldsets = (
        (_('👑 Core Identity'), {
            'fields': (('user', 'slug'), ('company_name', 'sector')),
            "classes": ("tab-content",),
        }),
        (_('📡 Real-Time Intent'), {
            'fields': (('current_search', 'collaboration_status'), 'right_now'),
            "classes": ("tab-content", "bg-gray-50"),
        }),
        (_('📜 Professional Narrative'), {
            'fields': (('location', 'mission_stmt'),),
            "classes": ("tab-content",),
        }),
        (_('⭐ System & Scoring'), {
            'fields': (('admin_rating', 'is_rating_locked'), 'last_signal_update', ('created_at', 'updated_at')),
            "classes": ("collapse",),
        }),
    )

    @display(description=_("User Identity"), ordering='user__last_name')
    def user_identity(self, obj):
        name = getattr(obj.user, 'full_name', str(obj.user))
        return format_html(
            '<div class="font-semibold text-gray-900">{}</div><div class="text-xs text-gray-500 font-mono">{}</div>',
            name, obj.slug or 'No slug'
        )

    @display(description=_("Rating"), ordering='admin_rating')
    def rating_display(self, obj):
        lock_icon = " 🔒" if obj.is_rating_locked else ""
        return format_html('{} <span class="text-xs">{}</span>', star_rating(obj.admin_rating), lock_icon)


# ==============================================================================
# 12. REMAINING SUPPORTING MODELS
# ==============================================================================

@admin.register(ExpertHeadline)
class ExpertHeadlineAdmin(ModelAdmin):
    list_display = ('profile_link', 'title', 'is_primary', 'order')
    list_filter = ('is_primary',)
    search_fields = ('title', 'profile__user__email', 'profile__user__first_name', 'profile__user__last_name')
    autocomplete_fields = ['profile']

    @display(description=_("Profile"))
    def profile_link(self, obj):
        url = get_admin_url(obj.profile)
        name = getattr(obj.profile.user, 'full_name', str(obj.profile.user))
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, name)


@admin.register(ProjectGalleryImage)
class ProjectGalleryImageAdmin(ModelAdmin):
    list_display = ('project_link', 'caption')
    search_fields = ('caption', 'project__title')
    autocomplete_fields = ['project']

    @display(description=_("Project"))
    def project_link(self, obj):
        url = get_admin_url(obj.project)
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, obj.project.title)


@admin.register(ProjectImage)
class VisionaryProjectImageAdmin(ModelAdmin):
    list_display = ('project_link', 'caption')
    search_fields = ('caption', 'project__name')
    autocomplete_fields = ['project']

    @display(description=_("Project"))
    def project_link(self, obj):
        url = get_admin_url(obj.project)
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, obj.project.name)
