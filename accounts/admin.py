from django import forms
from django.contrib import admin
from django.contrib.auth.forms import UserChangeForm
from django.core.exceptions import ObjectDoesNotExist
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

# =========================================================
# UNFOLD IMPORTS (Strictly Unfold - No Django Overrides)
# =========================================================
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

# =========================================================
# INTERNAL IMPORTS
# =========================================================
from operations.mixins import SecurityAuditMixin
from profiles.models import CompanyMember
from .forms import CustomUserAdminCreationForm
from .models import (
    ApplicationRequest, City, CommunityContributor, Country,
    CurrentStatus, CustomUser, FieldOfInterest, IDSequence,
    Institution, StaffUser, UniversalContactMethod, UniversalSocialLink
)


# =========================================================
# HELPER: DYNAMIC PROFILE RESOLVER (UPDATED FOR UNIFIED ARCHITECTURE)
# =========================================================
def get_user_profile(user):
    """
    Safely retrieves the Unified Portfolio.
    Replaces all legacy role-based profile checks.
    """
    try:
        # Relies on the related_name='portfolio' from UserProfile
        if hasattr(user, 'portfolio'):
            return user.portfolio
    except ObjectDoesNotExist:
        pass
    return None


# =========================================================
# 1. CUSTOM FORMS
# =========================================================

class CustomUserChangeForm(UserChangeForm):
    admin_rating = forms.IntegerField(
        min_value=0, max_value=5, required=False,
        label=_("Profile Admin Rating"),
        help_text=_(
            "Curate the user's rating (0-5). Automatically syncs to their Unified Portfolio.")
    )

    is_rating_locked = forms.BooleanField(
        required=False,
        label=_("Admin Rating Lock"),
        help_text=_("Check this to stop the AI Oracle from auto-updating this rating.")
    )

    class Meta:
        model = CustomUser
        fields = '__all__'
        field_classes = {'phone_number': forms.CharField}

    def clean_email(self):
        email = self.cleaned_data.get('email')
        return email if email else None

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        return phone if phone else None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            profile = get_user_profile(self.instance)
            if profile:
                self.fields['admin_rating'].initial = profile.admin_rating
                self.fields['is_rating_locked'].initial = getattr(profile, 'is_rating_locked', False)
            else:
                self.fields['admin_rating'].disabled = True
                self.fields['is_rating_locked'].disabled = True
                self.fields['admin_rating'].help_text = _(
                    "User does not have an active Unified Portfolio yet. Cannot set rating.")
                self.fields['is_rating_locked'].help_text = _("Portfolio required to lock rating.")


class StaffUserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(),
        required=False,
        help_text=_("Leave blank to keep current password.")
    )

    class Meta:
        model = StaffUser
        fields = ('full_name', 'phone_number', 'password', 'is_active', 'is_staff', 'is_superuser', 'groups')

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password"):
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            self.save_m2m()
        return user


# =========================================================
# 2. INLINES
# =========================================================

class CompanyMemberInline(TabularInline):
    model = CompanyMember
    extra = 0
    fields = ['company', 'role', 'job_title', 'is_active']
    readonly_fields = ['company']
    can_delete = False
    show_change_link = True
    tab = True


class SocialLinkInline(TabularInline):
    model = UniversalSocialLink
    extra = 1
    can_delete = True
    tab = True
    fields = ('platform_name', 'url', 'order')


class ContactMethodInline(TabularInline):
    model = UniversalContactMethod
    extra = 1
    can_delete = True
    tab = True
    fields = ('type', 'value')


class ApplicationRequestInline(TabularInline):
    model = ApplicationRequest
    extra = 0
    tab = True
    readonly_fields = ['submission_data', 'created_at']
    fields = ['role_type', 'status', 'cv_file', 'admin_notes', 'created_at']
    can_delete = True


class CityInline(TabularInline):
    model = City
    extra = 1
    fields = ['name', 'slug', 'is_verified']
    prepopulated_fields = {'slug': ('name',)}
    show_change_link = True


# =========================================================
# 3. MAIN USER ADMIN
# =========================================================

@admin.register(CustomUser)
class CustomUserAdmin(SecurityAuditMixin, ModelAdmin):
    add_form = CustomUserAdminCreationForm
    form = CustomUserChangeForm
    ordering = ('-date_joined',)

    list_display = [
        'display_header',
        'contact_details',
        'role_and_rating',
        'is_verified',
        'is_nexus_visible',
        'is_selected',
        'is_hero_avatar_selected',
        'is_home_profile_selected',
        'is_pinned_in_right_now',
        'is_banned_from_right_now',
        'is_active',
    ]

    list_editable = [
        'is_verified',
        'is_nexus_visible',
        'is_selected',
        'is_hero_avatar_selected',
        'is_home_profile_selected',
        'is_pinned_in_right_now',
        'is_banned_from_right_now',
        'is_active'
    ]

    list_filter = [
        'role',
        'is_hero_avatar_selected',
        'is_home_profile_selected',
        'is_selected',
        'is_nexus_visible',
        'is_pinned_in_right_now',
        'is_banned_from_right_now',
        'is_verified',
        'is_active',
        'date_joined'
    ]

    search_fields = ['phone_number', 'email', 'full_name', 'telegram_handle', 'corelink_id']
    inlines = [CompanyMemberInline, ContactMethodInline, SocialLinkInline, ApplicationRequestInline]

    fieldsets = (
        (_("Identity & Role"), {
            "fields": (
                'full_name', 'telegram_handle', 'role', 'corelink_id',
                'current_location', 'avatar', 'cover_image', 'is_verified',
                ('admin_rating', 'is_rating_locked')
            ),
            "classes": ["tab"]
        }),
        (_("🏠 Home Page Curation"), {
            "fields": (
                'is_hero_avatar_selected',
                'is_home_profile_selected',
            ),
            "description": "Control exactly who appears on the public landing page (Hero avatars and Talent Network cards).",
            "classes": ["collapse"]
        }),
        (_("🛡️ Feed Control & Moderation"), {
            "fields": (
                'is_nexus_visible',
                'is_selected',
                'is_pinned_in_right_now',
                'is_banned_from_right_now'
            ),
            "description": "Toggle visibility across the Nexus and Right Now feeds.",
            "classes": ["collapse"]
        }),
        (_("Security & Access"), {
            "fields": ('phone_number', 'email', 'is_email_verified', 'password', 'is_active', 'is_staff',
                       'is_superuser'),
            "classes": ["tab"]
        }),
        (_("Permissions & Groups"), {
            "fields": ('groups', 'user_permissions'),
            "classes": ["tab"]
        }),
        (_("Timestamps"), {
            "fields": ('date_joined', 'last_login'),
            "classes": ["collapse"]
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # PERFORMANCE FIX: Replaced legacy profiles with the single 'portfolio' relation
        return qs.select_related('portfolio')

    def save_model(self, request, obj, form, change):
        if getattr(obj, 'email', None) == "":
            obj.email = None
        if getattr(obj, 'phone_number', None) == "":
            obj.phone_number = None

        super().save_model(request, obj, form, change)

        profile = get_user_profile(obj)
        if profile:
            rating = form.cleaned_data.get('admin_rating')
            is_locked = form.cleaned_data.get('is_rating_locked')
            update_fields = []

            if rating is not None and getattr(profile, 'admin_rating', None) != rating:
                profile.admin_rating = rating
                update_fields.append('admin_rating')

            if is_locked is not None and getattr(profile, 'is_rating_locked', None) != is_locked:
                profile.is_rating_locked = is_locked
                update_fields.append('is_rating_locked')

            if update_fields:
                profile.save(update_fields=update_fields)

    # --- 🎯 UI FIXES: FORCE WRAPPING AND STOP ROW CLICK ---

    # INJECTING CSS HERE: This keeps the columns permanently sticky to the top when scrolling without touching settings!
    STICKY_HEADER_CSS = mark_safe(
        str(_("User Identity")) +
        '<style>'
        '#result_list thead th { position: sticky !important; top: 0 !important; z-index: 40 !important; outline: 1px solid rgba(128,128,128,0.1); } '
        '.dark #result_list thead th { background-color: #111827 !important; } '
        '#result_list thead th { background-color: #f9fafb !important; }'
        '</style>'
    )

    @display(description=STICKY_HEADER_CSS)
    def display_header(self, obj):
        image_url = obj.avatar.url if obj.avatar else f"https://ui-avatars.com/api/?name={obj.full_name}&background=EBF4FF&color=7F9CF5"

        # Company Badge Logic
        company_html = ""
        memberships = obj.company_memberships.filter(is_active=True).select_related('company')
        if memberships.exists():
            companies = ", ".join([m.company.name for m in memberships])
            company_html = f'<div style="font-size: 10px; font-weight: bold; color: #b8860b; margin-top: 2px;">🏢 {companies}</div>'
        elif str(getattr(obj, 'role', '')).upper() == 'FOUNDER':
            company_html = '<div style="font-size: 10px; font-weight: bold; color: #854d0e; margin-top: 2px;">👑 Independent Founder</div>'

        # Fetch the exact absolute URL defined in your models.py
        try:
            profile_url = obj.get_absolute_url()
        except Exception:
            profile_url = f"/profile/{obj.corelink_id or obj.id}/"

        # Sleek, professional View Profile link with SVG embedded indicator
        link_html = f'''
            <div style="margin-top: 8px;">
                <a href="{profile_url}" target="_blank" onclick="event.stopPropagation();" 
                   style="display: inline-flex; align-items: center; gap: 3px; font-size: 10px; font-weight: 600; color: #4338ca; text-decoration: none; text-transform: uppercase; letter-spacing: 0.5px;">
                    View Profile 
                    <svg width="10" height="10" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M7 17l9.2-9.2M17 17V7H7"/>
                    </svg>
                </a>
            </div>
        '''

        # Enforced max-width: 250px so it forces the table to shrink
        return format_html(
            '''
            <div style="display: flex; align-items: flex-start; gap: 10px; min-width: 180px; max-width: 250px; white-space: normal;">
                <img src="{}" style="width: 36px; height: 36px; border-radius: 50%; object-fit: cover; border: 1px solid #eee; flex-shrink: 0;" />
                <div style="display: flex; flex-direction: column; overflow: hidden;">
                    <span style="font-weight: 600; font-size: 13px; line-height: 1.2;">{}</span>
                    <span style="font-size: 11px; color: #6b7280; margin-top: 2px;">{}</span>
                    {}
                    {}
                </div>
            </div>
            ''',
            image_url, obj.full_name, obj.telegram_handle or "",
            mark_safe(company_html), mark_safe(link_html)
        )

    @display(description=_("Contact Info"))
    def contact_details(self, obj):
        email_status = '<span style="color: #16a34a;" title="Verified Email">✅</span>' if obj.is_email_verified else '<span style="color: #d97706;" title="Unverified Email">⏳</span>'
        phone = obj.phone_number or '<span style="color: #9ca3af;">No Phone</span>'
        email = obj.email or '<span style="color: #9ca3af;">No Email</span>'

        # Enforced max-width: 200px and word-wrap to prevent table stretching
        return format_html(
            '<div style="font-size: 11px; line-height: 1.5; min-width: 140px; max-width: 200px; white-space: normal; word-wrap: break-word;">'
            '<strong>📞</strong> {}<br>'
            '<div style="margin-top: 4px;"><strong>📧</strong> {} {}</div>'
            '</div>',
            mark_safe(phone), mark_safe(email), mark_safe(email_status)
        )

    @display(description=_("Role & Rating"))
    def role_and_rating(self, obj):
        profile = get_user_profile(obj)
        rating_html = ""
        if profile:
            rating = profile.admin_rating
            is_locked = getattr(profile, 'is_rating_locked', False)
            stars = "⭐" * rating + "☆" * (5 - rating)
            lock_icon = ' <span title="Rating Locked">🔒</span>' if is_locked else ''
            rating_html = f'<div style="color: #ca8a04; font-size: 11px; margin-top: 6px; white-space: nowrap;" title="Rating: {rating}/5">{stars}{lock_icon}</div>'
        else:
            rating_html = '<div style="color: #9ca3af; font-size: 10px; margin-top: 6px;">No Profile</div>'

        role_badge = f'<span style="background: #e0e7ff; color: #3730a3; padding: 3px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; border: 1px solid #c7d2fe; display: inline-block;">{obj.role}</span>'

        return format_html('<div style="min-width: 90px;">{}{}</div>', mark_safe(role_badge), mark_safe(rating_html))

    # --- LOCKDOWN LOGIC ---
    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return [
                'full_name', 'phone_number', 'telegram_handle', 'role', 'corelink_id',
                'current_location', 'avatar', 'cover_image', 'is_active', 'is_staff', 'is_superuser', 'groups',
                'user_permissions', 'date_joined', 'last_login', 'password'
            ]
        return self.readonly_fields

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not request.user.is_superuser:
            return [fs for fs in fieldsets if fs[0] == _("Identity & Role")]
        return fieldsets

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_inlines(self, request, obj=None):
        if not request.user.is_superuser:
            return [CompanyMemberInline]
        return self.inlines


# =========================================================
# 4. SECONDARY ADMINS
# =========================================================

@admin.register(ApplicationRequest)
class ApplicationRequestAdmin(SecurityAuditMixin, ModelAdmin):
    ordering = ('-created_at',)
    list_display = ['user', 'role_type', 'status_badge', 'display_cv', 'created_at']
    list_filter = ['status', 'role_type', 'created_at']
    search_fields = ['user__full_name', 'user__phone_number']
    readonly_fields = ['submission_data']

    @display(description=_("Status"))
    def status_badge(self, obj):
        colors = {"PENDING": ("#ca8a04", "#fef08a"), "APPROVED": ("#16a34a", "#dcfce7"),
                  "REJECTED": ("#dc2626", "#fee2e2")}
        text_color, bg_color = colors.get(obj.status, ("#4b5563", "#f3f4f6"))
        return format_html(
            '<span style="background: {}; color: {}; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;">{}</span>',
            bg_color, text_color, obj.get_status_display()
        )

    @display(description=_("CV Document"))
    def display_cv(self, obj):
        if obj.cv_file:
            return format_html('<a href="{}" target="_blank" style="color: #2563eb; font-weight: bold;">📄 View CV</a>',
                               obj.cv_file.url)
        return mark_safe('<span style="color: #9ca3af; font-size: 11px;">No CV</span>')


@admin.register(CommunityContributor)
class CommunityContributorAdmin(SecurityAuditMixin, ModelAdmin):
    ordering = ('-created_at',)
    list_display = ['full_name', 'telegram_username', 'contribution_area', 'contact_status_badge', 'created_at']
    list_filter = ['is_contacted', 'created_at']
    search_fields = ['full_name', 'telegram_username', 'contribution_area']

    @display(description=_("Contact Status"))
    def contact_status_badge(self, obj):
        if obj.is_contacted:
            return format_html(
                '<span style="background: #dcfce7; color: #16a34a; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;">Contacted</span>')
        return format_html(
            '<span style="background: #fee2e2; color: #dc2626; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold;">Waiting</span>')


@admin.register(IDSequence)
class IDSequenceAdmin(ModelAdmin):
    list_display = ['prefix', 'year', 'last_number']


@admin.register(StaffUser)
class StaffUserAdmin(SecurityAuditMixin, ModelAdmin):
    form = StaffUserForm
    list_display = ['display_header', 'phone_number', 'is_active', 'is_superuser']

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_staff=True)

    @display(description=_("Staff Member"))
    def display_header(self, obj):
        image_url = obj.avatar.url if obj.avatar else f"https://ui-avatars.com/api/?name={obj.full_name}"
        return format_html(
            '<div style="display: flex; align-items: center; gap: 10px;">'
            '<img src="{}" style="width: 32px; height: 32px; border-radius: 50%; object-fit: cover;" /><b>{}</b></div>',
            image_url, obj.full_name
        )


# =========================================================
# 5. LOCATION ADMINS
# =========================================================

@admin.register(Country)
class CountryAdmin(ModelAdmin):
    list_display = ['name', 'slug', 'is_verified', 'city_count', 'created_at']
    list_filter = ['is_verified']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [CityInline]

    @display(description=_("Cities"))
    def city_count(self, obj):
        return obj.city_set.count()


@admin.register(City)
class CityAdmin(ModelAdmin):
    list_display = ['name', 'Country', 'slug', 'is_verified', 'created_at']
    list_filter = ['is_verified', 'Country']
    search_fields = ['name', 'Country__name']
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['Country']


# =========================================================
# 6. INSTITUTION & FIELD OF INTEREST ADMINS
# =========================================================

@admin.register(Institution)
class InstitutionAdmin(ModelAdmin):
    list_display = ['name', 'City', 'slug', 'is_verified', 'created_at']
    list_filter = ['is_verified', 'City']
    search_fields = ['name', 'City__name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(FieldOfInterest)
class FieldOfInterestAdmin(ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']


@admin.register(CurrentStatus)
class CurrentStatusAdmin(ModelAdmin):
    list_display = ['id', 'name']
    search_fields = ['name']