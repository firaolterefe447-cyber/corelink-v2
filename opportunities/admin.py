from django.contrib import admin
from django import forms
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.db.models import Count
from django.shortcuts import redirect
from django.contrib import messages

from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display, action

from .models import Skill, JobPost, JobApplication


# ==============================================================================
# 1. THE RAPID DATA ENTRY FORM (COLD START SOLVER)
# ==============================================================================
class RapidJobPostAdminForm(forms.ModelForm):
    """
    NO MORE WYSIWYG! Pure raw text area to preserve exact Telegram/LinkedIn spacing.
    """

    class Meta:
        model = JobPost
        fields = '__all__'
        # ✅ PURE TEXTAREA: Forces the browser to keep 100% of your pasted structure.
        widgets = {
            'description': forms.Textarea(attrs={
                'id': 'custom_desc',
                'rows': 25,
                'style': 'width: 100%; max-width: 100%; font-size: 15px; padding: 16px; line-height: 1.8; border-radius: 8px; border: 1px solid #cbd5e1; background-color: #f8fafc; font-family: inherit;'
            }),
            'challenge_description': forms.Textarea(attrs={
                'id': 'custom_chall',
                'rows': 12,
                'style': 'width: 100%; max-width: 100%; font-size: 15px; padding: 16px; line-height: 1.8; border-radius: 8px; border: 1px solid #cbd5e1; background-color: #f8fafc; font-family: inherit;'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'posted_by' in self.fields:
            self.fields['posted_by'].required = False
        if 'company' in self.fields:
            self.fields['company'].required = False

        # ✅ MAGIC JAVASCRIPT: Custom formatting toolbar that doesn't ruin your text!
        toolbar_script = """
            <script>
                function formatText(id, openTag, closeTag) {
                    var el = document.getElementById(id);
                    if (!el) return;
                    var start = el.selectionStart;
                    var end = el.selectionEnd;
                    var text = el.value;
                    var before = text.substring(0, start);
                    var selected = text.substring(start, end);
                    var after = text.substring(end, text.length);
                    el.value = before + openTag + selected + closeTag + after;
                    el.focus();
                    el.setSelectionRange(start + openTag.length, end + openTag.length);
                }
            </script>
        """

        if 'description' in self.fields:
            self.fields['description'].help_text = mark_safe(
                toolbar_script + """
                <div style="margin-bottom: 10px; display: flex; gap: 8px; background: #e2e8f0; padding: 8px; border-radius: 6px; align-items: center;">
                    <span style="font-size: 13px; font-weight: bold; color: #475569; margin-right: 10px;">Format:</span>
                    <button type="button" onclick="formatText('custom_desc', '<b>', '</b>')" style="padding: 6px 14px; background: white; border: 1px solid #cbd5e1; border-radius: 6px; font-weight: 900; cursor: pointer; color: #0f172a; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">B</button>
                    <button type="button" onclick="formatText('custom_desc', '<i>', '</i>')" style="padding: 6px 14px; background: white; border: 1px solid #cbd5e1; border-radius: 6px; font-style: italic; cursor: pointer; color: #0f172a; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">I</button>
                    <button type="button" onclick="formatText('custom_desc', '• ', '')" style="padding: 6px 14px; background: white; border: 1px solid #cbd5e1; border-radius: 6px; cursor: pointer; color: #0f172a; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">Bullet Point</button>
                </div>
                <div style="color: #16a34a; font-size: 14px; margin-top: 5px;">
                    ✅ <b>Freedom Mode:</b> Paste anything from Telegram or LinkedIn here. It will keep <b>100% of your exact line breaks and spaces</b>. Highlight text and click 'B' to bold.
                </div>
                """
            )

        if 'challenge_description' in self.fields:
            self.fields['challenge_description'].help_text = mark_safe("""
                <div style="margin-bottom: 10px; display: flex; gap: 8px; background: #e2e8f0; padding: 8px; border-radius: 6px; align-items: center;">
                    <span style="font-size: 13px; font-weight: bold; color: #475569; margin-right: 10px;">Format:</span>
                    <button type="button" onclick="formatText('custom_chall', '<b>', '</b>')" style="padding: 6px 14px; background: white; border: 1px solid #cbd5e1; border-radius: 6px; font-weight: 900; cursor: pointer; color: #0f172a; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">B</button>
                    <button type="button" onclick="formatText('custom_chall', '• ', '')" style="padding: 6px 14px; background: white; border: 1px solid #cbd5e1; border-radius: 6px; cursor: pointer; color: #0f172a; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">Bullet Point</button>
                </div>
            """)

        # IF CREATING A NEW JOB (Not editing an existing one)
        if not self.instance.pk:
            self.initial['is_external'] = True
            self.initial['is_open_ended'] = True
            self.initial['status'] = JobPost.Status.ACTIVE  # Auto-publish!
            self.initial['source_name'] = 'Telegram / LinkedIn'
            self.initial['location'] = 'Addis Ababa'
            self.initial['level'] = JobPost.ExperienceLevel.ANY  # Default level


# ==============================================================================
# 2. SKILL TAXONOMY & AI ALIASES
# ==============================================================================
@admin.register(Skill)
class SkillAdmin(ModelAdmin):
    list_display = ('name', 'category', 'usage_count', 'slug')
    list_filter = ('category',)
    search_fields = ('name', 'category', 'ai_aliases')
    ordering = ('name',)

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category')
        }),
        (_('🤖 AI Taxonomy'), {
            'fields': ('ai_aliases',),
            'description': "JSON list of synonyms (e.g.['ReactJS', 'React.js']) so the AI knows they are the same.",
        }),
    )

    @display(description="Jobs Linked")
    def usage_count(self, obj):
        return getattr(obj, 'opportunity_count', 0)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(opportunity_count=Count('opportunities'))


# ==============================================================================
# 3. APPLICATION INLINE (THE GRAVITY LINK)
# ==============================================================================
class JobApplicationInline(TabularInline):
    model = JobApplication
    extra = 0
    can_delete = False
    show_change_link = True
    tab = True

    readonly_fields = ('applicant', 'match_score_display', 'status_badge', 'created_at')
    fields = ('applicant', 'status', 'status_badge', 'match_score_display', 'cover_note', 'attached_project',
              'created_at')

    formfield_overrides = {
        forms.CharField: {'widget': forms.Textarea(attrs={'rows': 2, 'cols': 40})},
    }

    @display(description=_("Status"))
    def status_badge(self, obj):
        return obj.status

    @display(description=_("🤖 AI Match"))
    def match_score_display(self, obj):
        color = "text-emerald-600" if obj.match_score > 80 else "text-amber-500" if obj.match_score > 50 else "text-red-600"
        return format_html('<span class="font-bold {}">{}%</span>', color, round(obj.match_score, 1))


# ==============================================================================
# 4. THE MASTER JOB ADMIN (OPTIMIZED FOR SPEED & GOD-MODE)
# ==============================================================================
@admin.register(JobPost)
class JobPostAdmin(ModelAdmin):
    form = RapidJobPostAdminForm
    inlines = [JobApplicationInline]
    save_as = True

    list_display = (
        'title',
        'attribution_badge',
        'status_badge',
        'job_type_badge',
        'level_badge',
        'is_external',
        'views_count',
        'applications_count',
        'published_at'
    )

    list_editable = ('is_external',)
    list_filter = ('status', 'source_name', 'is_external', 'job_type', 'level', 'is_remote', 'requires_challenge')
    search_fields = ('title', 'description', 'external_company_name', 'location', 'submitter_contact')

    autocomplete_fields = ('posted_by', 'company')
    filter_horizontal = ('required_skills',)

    fieldsets = (
        (_('⚡ 1. The Quick Drop (Job Core Info)'), {
            'fields': (
                'status',
                'title',
                'description',
                ('job_type', 'level', 'location', 'is_remote'),
            ),
            'description': "Set the primary job information and text payload here.",
            "classes": ("tab-content",),
        }),
        (_('🏢 2. External / Internal Attribution'), {
            'fields': (
                'is_external',
                ('external_company_name', 'external_url'),
                'external_company_logo',
                ('company', 'posted_by', 'is_official_admin_post'),
                'submitter_contact',
                'source_name',
            ),
            'description': "Link external URLs, manage Guest Posts (Contact Info), or associate with registered platform Companies/Users.",
            "classes": ("tab-content",),
        }),
        (_('⏳ 3. Timing & URLs'), {
            'fields': (
                ('deadline_date', 'deadline_text', 'is_open_ended'),
                ('published_at', 'slug'),
            ),
            'description': "Control deadlines and exactly when the post went live.",
            "classes": ("tab-content",),
        }),
        (_('💰 4. Financials (Optional)'), {
            'fields': (
                'compensation_text',
                ('salary_min', 'salary_max'),
            ),
            "classes": ("collapse",),
        }),
        (_('🖼️ 5. Branding & Skills'), {
            'fields': (
                'cover_image',
                'required_skills',
            ),
            "classes": ("collapse",),
        }),
        (_('🏆 6. CoreLink Innovation (Challenge Mode)'), {
            'fields': (
                'requires_challenge',
                'challenge_description',
            ),
            "classes": ("collapse",),
        }),
        (_('⚙️ 7. System, Metrics & AI (Fully Editable)'), {
            'fields': (
                ('views_count', 'applications_count'),
                'ai_metadata',
            ),
            'description': "⚠️ GOD MODE: You can manually override views and application counts here to simulate platform traction.",
            'classes': ('collapse',),
        }),
    )

    actions = ['approve_jobs', 'reject_jobs', 'close_jobs', 'mark_as_telegram']
    actions_row = ['make_live_button', 'close_job_button']

    def save_model(self, request, obj, form, change):
        if getattr(obj, 'posted_by_id', None) is None and not obj.submitter_contact:
            obj.posted_by = request.user

        if not change:
            if not obj.company and not obj.is_external and not obj.submitter_contact:
                obj.is_official_admin_post = True

            if obj.status == JobPost.Status.ACTIVE and not obj.published_at:
                obj.published_at = timezone.now()

        super().save_model(request, obj, form, change)

    @display(description="Identity / Source")
    def attribution_badge(self, obj):
        if obj.submitter_contact:
            return format_html(
                '<div class="flex flex-col">'
                '<span class="text-rose-600 font-bold uppercase text-[11px] tracking-wider mb-0.5">GUEST POST</span>'
                '<span class="text-slate-500 text-xs truncate max-w-[150px]" title="{0}">{0}</span>'
                '</div>',
                obj.submitter_contact
            )
        elif obj.is_official_admin_post:
            return format_html(
                '<div class="flex items-center gap-1.5 text-purple-700 font-extrabold">'
                '<span class="w-5 h-5 rounded-full bg-purple-100 flex items-center justify-center">★</span>CoreLink Admin'
                '</div>'
            )
        elif obj.company:
            return format_html('<div class="flex items-center gap-1.5 text-blue-700 font-bold">🏢 {}</div>',
                               obj.company.name)
        elif obj.posted_by:
            name = obj.posted_by.get_full_name() or obj.posted_by.username
            return format_html('<div class="flex items-center gap-1.5 text-teal-700 font-bold">👤 {}</div>', name)
        elif obj.external_company_name:
            return format_html('<div class="flex items-center gap-1.5 text-amber-700 font-bold">🌐 {}</div>',
                               obj.external_company_name)
        return "-"

    @display(description=_("Status"))
    def status_badge(self, obj):
        return obj.status

    @display(description=_("Job Type"))
    def job_type_badge(self, obj):
        return obj.job_type

    @display(description=_("Level"))
    def level_badge(self, obj):
        return obj.level

    @action(description="🟢 LIVE")
    def make_live_button(self, request, object_id):
        job = self.get_object(request, object_id)
        if job and job.status != JobPost.Status.ACTIVE:
            job.status = JobPost.Status.ACTIVE
            if not job.published_at:
                job.published_at = timezone.now()
            job.save()
            messages.success(request, f"🚀 '{job.title}' is now LIVE on the platform!")
        return redirect(request.META.get('HTTP_REFERER', 'admin:opportunities_jobpost_changelist'))

    @action(description="🔒 CLOSE")
    def close_job_button(self, request, object_id):
        job = self.get_object(request, object_id)
        if job and job.status != JobPost.Status.CLOSED:
            job.status = JobPost.Status.CLOSED
            job.save()
            messages.warning(request, f"🔒 '{job.title}' has been closed.")
        return redirect(request.META.get('HTTP_REFERER', 'admin:opportunities_jobpost_changelist'))

    @action(description="🟢 Set Selected Live (Active)")
    def approve_jobs(self, request, queryset):
        queryset.update(status=JobPost.Status.ACTIVE, published_at=timezone.now())

    @action(description="🔴 Reject Selected")
    def reject_jobs(self, request, queryset):
        queryset.update(status=JobPost.Status.REJECTED)

    @action(description="🔒 Close Selected")
    def close_jobs(self, request, queryset):
        queryset.update(status=JobPost.Status.CLOSED)

    @action(description="📱 Mark Source as Telegram")
    def mark_as_telegram(self, request, queryset):
        queryset.update(source_name="Telegram")


# ==============================================================================
# 5. GLOBAL APPLICATION ADMIN (THE GRAVITY LINK OVERSIGHT)
# ==============================================================================
@admin.register(JobApplication)
class JobApplicationAdmin(ModelAdmin):
    list_display = ('applicant', 'job', 'status_badge', 'match_score_display', 'has_project_attached', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('applicant__username', 'applicant__first_name', 'job__title', 'job__external_company_name')

    # ✅ FIX: Removed 'attached_project' from here
    autocomplete_fields = ('job', 'applicant')

    # ✅ FIX: Added raw_id_fields so you can still search/select the project without breaking Django Admin
    raw_id_fields = ('attached_project',)

    readonly_fields = ()

    fieldsets = (
        (_('Applicant & Job'), {
            'fields': (('applicant', 'job'), 'status')
        }),
        (_('The Pitch & Proof'), {
            'fields': ('cover_note', 'attached_project')
        }),
        (_('🤖 AI Insights (Editable)'), {
            'fields': (('match_score', 'ai_analysis'),),
            'description': "AI-generated reasoning for candidate fit. Admins can manually override the score if needed.",
        }),
    )

    @display(description=_("Status"))
    def status_badge(self, obj):
        return obj.status

    @display(description=_("🤖 AI Score"))
    def match_score_display(self, obj):
        color = "text-emerald-600" if obj.match_score > 80 else "text-amber-500" if obj.match_score > 50 else "text-red-600"
        return format_html('<span class="font-bold {}">{}%</span>', color, round(obj.match_score, 1))

    @display(description=_("Proof of Work"), boolean=True)
    def has_project_attached(self, obj):
        return bool(obj.attached_project)