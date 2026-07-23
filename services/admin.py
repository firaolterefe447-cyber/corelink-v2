"""
Service Admin Configuration
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.contrib.admin import ModelAdmin, TabularInline, StackedInline
from django.contrib.admin.decorators import display
from django import forms

from .models import Service, ServiceGallery, ServiceCategory, ServiceSubcategory, ServiceTag, ServiceType


def get_admin_url(obj):
    """Get admin URL for an object."""
    from django.urls import reverse
    return reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', args=[obj.pk])


class ServiceAdminForm(forms.ModelForm):
    """Custom admin form for Service with dynamic subcategory filtering."""
    
    class Meta:
        model = Service
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Include all subcategories for validation purposes
        # The category-subcategory relationship is validated in clean_subcategory
        self.fields['subcategory'].queryset = ServiceSubcategory.objects.all().order_by('category', 'order', 'name')
    
    def clean_subcategory(self):
        """Ensure subcategory belongs to selected category."""
        category = self.cleaned_data.get('category')
        subcategory = self.cleaned_data.get('subcategory')
        
        if subcategory and category:
            if subcategory.category != category:
                raise forms.ValidationError(_("This subcategory does not belong to the selected category."))
        
        return subcategory


class ServiceSubcategoryInline(TabularInline):
    """Inline for managing subcategories within a category."""
    model = ServiceSubcategory
    extra = 0
    fields = ('name', 'slug', 'order', 'is_active')
    readonly_fields = ()


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(ModelAdmin):
    """Admin interface for Service Categories."""
    list_display = ('name_with_icon', 'slug', 'service_count', 'is_active_badge', 'order', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ServiceSubcategoryInline]
    list_editable = ('order',)

    fieldsets = (
        (None, {'fields': ('name', 'slug', 'description')}),
        ('Branding', {'fields': ('icon', 'color')}),
        ('Settings', {'fields': (('is_active', 'order'),)}),
    )

    @display(description=_("Category"))
    def name_with_icon(self, obj):
        if obj.icon:
            return format_html('<img src="{}" class="h-6 w-6 rounded inline mr-2" /> {}', obj.icon.url, obj.name)
        return obj.name

    @display(description=_("Services"))
    def service_count(self, obj):
        return obj.services.count()

    @display(description=_("Status"))
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="bg-emerald-500 text-white px-2 py-1 rounded text-xs font-semibold">Active</span>')
        return format_html('<span class="bg-gray-400 text-white px-2 py-1 rounded text-xs font-semibold">Inactive</span>')


@admin.register(ServiceSubcategory)
class ServiceSubcategoryAdmin(ModelAdmin):
    """Admin interface for Service Subcategories."""
    list_display = ('name', 'category_link', 'slug', 'service_count', 'is_active_badge', 'order')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'slug', 'description', 'category__name')
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['category']
    list_editable = ('order',)

    fieldsets = (
        (None, {'fields': ('category', 'name', 'slug', 'description')}),
        ('Settings', {'fields': (('is_active', 'order'),)}),
    )

    @display(description=_("Category"))
    def category_link(self, obj):
        url = get_admin_url(obj.category)
        return format_html('<a href="{}" class="text-blue-600 hover:text-blue-900 font-medium">{}</a>', url, obj.category.name)

    @display(description=_("Services"))
    def service_count(self, obj):
        return obj.services.count()

    @display(description=_("Status"))
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="bg-emerald-500 text-white px-2 py-1 rounded text-xs font-semibold">Active</span>')
        return format_html('<span class="bg-gray-400 text-white px-2 py-1 rounded text-xs font-semibold">Inactive</span>')


@admin.register(ServiceTag)
class ServiceTagAdmin(ModelAdmin):
    """Admin interface for Service Tags."""
    list_display = ('name', 'slug', 'usage_count', 'is_featured', 'created_at')
    list_filter = ('is_featured', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_featured',)

    fieldsets = (
        (None, {'fields': ('name', 'slug', 'description')}),
        ('Settings', {'fields': ('is_featured',)}),
    )


@admin.register(ServiceType)
class ServiceTypeAdmin(ModelAdmin):
    """Admin interface for Service Types."""
    list_display = ('name_with_icon', 'slug', 'service_count', 'is_active_badge', 'order', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('order',)

    fieldsets = (
        (None, {'fields': ('name', 'slug', 'description')}),
        ('Display', {'fields': ('icon',)}),
        ('Settings', {'fields': (('is_active', 'order'),)}),
    )

    @display(description=_("Type"))
    def name_with_icon(self, obj):
        if obj.icon:
            return format_html('{} {}', obj.icon, obj.name)
        return obj.name

    @display(description=_("Services"))
    def service_count(self, obj):
        return obj.services.count()

    @display(description=_("Status"))
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="bg-emerald-500 text-white px-2 py-1 rounded text-xs font-semibold">Active</span>')
        return format_html('<span class="bg-gray-400 text-white px-2 py-1 rounded text-xs font-semibold">Inactive</span>')


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
    form = ServiceAdminForm
    change_form_template = 'admin/services/change_form.html'
    list_display = ('title', 'profile_link', 'category_badge', 'is_active_badge', 'gallery_count', 'created_at')
    list_filter = ('is_active', 'category', 'created_at')
    search_fields = ('title', 'description', 'profile__user__email', 'tags__name')
    autocomplete_fields = ['profile']
    filter_horizontal = ['tags']
    inlines = [ServiceGalleryInline]
    readonly_fields = ('created_at',)

    fieldsets = (
        ('📝 Basic Information', {
            'fields': ('profile', 'title', 'description'),
            'classes': ('wide',),
        }),
        ('🏷️ Classification', {
            'fields': ('category', 'subcategory', 'tags'),
            'classes': ('wide',),
        }),
        ('⚙️ Settings', {
            'fields': (('is_active', 'order'),),
            'classes': ('collapse',),
        }),
        ('📅 Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    class Media:
        js = ('admin/js/jquery.init.js', 'services/js/admin_service.js')
        css = {
            'all': ('services/css/admin_service.css',)
        }

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # Trigger Oracle update after service changes
        if obj.profile and obj.profile.user:
            from profiles.automatic_rating import CoreLinkOracle
            try:
                CoreLinkOracle.update_user_rating(obj.profile.user.id, force_update=True)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"[ORACLE ADMIN] Failed to update rating for user {obj.profile.user.id}: {str(e)}", exc_info=True)

    def delete_model(self, request, obj):
        user_id = obj.profile.user.id if obj.profile and obj.profile.user else None
        super().delete_model(request, obj)
        
        # Trigger Oracle update after service deletion
        if user_id:
            from profiles.automatic_rating import CoreLinkOracle
            try:
                CoreLinkOracle.update_user_rating(user_id, force_update=True)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"[ORACLE ADMIN] Failed to update rating for user {user_id}: {str(e)}", exc_info=True)

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

    @display(description=_("Category"))
    def category_badge(self, obj):
        if obj.category:
            return format_html(
                '<span class="px-2 py-1 rounded text-xs font-semibold" style="background-color: {}; color: white;">{}</span>',
                obj.category.color, obj.category.name
            )
        return format_html('<span class="text-gray-400 text-xs">Uncategorized</span>')

    @display(description=_("Type"))
    def service_type_badge(self, obj):
        if obj.service_type:
            icon = obj.service_type.icon if obj.service_type.icon else ''
            return format_html('<span class="bg-slate-100 text-slate-700 px-2 py-1 rounded text-xs font-semibold">{} {}</span>', icon, obj.service_type.name)
        return '-'


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
