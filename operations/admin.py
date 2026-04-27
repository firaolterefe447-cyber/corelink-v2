from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe  # 👈 Added this import
from unfold.admin import ModelAdmin

# Import our Mixin
from .mixins import SecurityAuditMixin
from .models import AchievementClaim, FamilyUnit, FamilyMembership, AuditLog

# =========================================================
# 1. THE SECURITY BLACKBOX (SUPERUSER ONLY)
# =========================================================

@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    # Visuals
    list_display = ('timestamp', 'admin_link', 'action', 'target_user', 'ip_address', 'admin_status')
    list_filter = ('action', 'timestamp', 'admin')
    search_fields = ('admin__username', 'target_user__username', 'action', 'id')
    readonly_fields = ('timestamp', 'admin', 'target_user', 'action', 'details', 'ip_address')
    list_per_page = 50

    # --- PERMISSIONS: TOTAL LOCKDOWN ---
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

    # --- SUPERUSER UTILITIES ---
    @admin.display(description="Admin Name")
    def admin_link(self, obj):
        if obj.admin:
            link = reverse("admin:accounts_customuser_change", args=[obj.admin.id])
            # This one is fine because it has {} placeholders
            return format_html('<a href="{}" class="font-bold text-blue-600">{}</a>', link, obj.admin.username)
        return "Deleted Admin"

    @admin.display(description="Status")
    def admin_status(self, obj):
        """Visual check if the Admin performing the action is currently Active or Blocked"""
        if obj.admin:
            if obj.admin.is_active:
                # 👇 CHANGED: format_html -> mark_safe (Fixes the Crash)
                return mark_safe('<span style="color:green;">● Active</span>')
            # 👇 CHANGED: format_html -> mark_safe
            return mark_safe('<span style="color:red;">● BLOCKED</span>')
        return "-"

    actions = ['block_bad_admin']

    @admin.action(description="🚫 EMERGENCY: Block Selected Admin(s)")
    def block_bad_admin(self, request, queryset):
        if not request.user.is_superuser: return
        count = 0
        for log in queryset:
            if log.admin and not log.admin.is_superuser:
                log.admin.is_active = False
                log.admin.save()
                count += 1
        self.message_user(request, f"Blocked {count} admin(s).")

# =========================================================
# 2. OPERATIONAL TABLES (MONITORED)
# =========================================================

@admin.register(AchievementClaim)
class AchievementClaimAdmin(SecurityAuditMixin, ModelAdmin):
    list_display = ['user', 'title', 'status', 'created_at']
    list_filter = ['status']
    actions = ['approve_claims']

    def approve_claims(self, request, queryset):
        queryset.update(status='APPROVED')
    approve_claims.short_description = "Approve Selected Claims"

class FamilyMemberInline(admin.TabularInline):
    model = FamilyMembership
    extra = 0

@admin.register(FamilyUnit)
class FamilyUnitAdmin(SecurityAuditMixin, ModelAdmin):
    list_display = ['name', 'lead_mentor', 'telegram_link']
    inlines = [FamilyMemberInline]