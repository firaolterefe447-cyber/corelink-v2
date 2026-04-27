"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CORELINK UNIFIED PORTFOLIO FORMS                          ║
║                    Universal & Inclusive for ALL Professions                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
import logging
from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import date

logger = logging.getLogger(__name__)

# ==============================================================================
# 0. MODEL IMPORTS
# ==============================================================================
try:
    from accounts.models import CustomUser, UniversalSocialLink, UniversalContactMethod
    from accounts.models import Country, City, Institution, FieldOfInterest, CurrentStatus
except ImportError:
    Country = City = Institution = FieldOfInterest = CurrentStatus = None

from profiles.models.new_unified_profile import (
    UserProfile, ProfileHeadline, Skill, Credential, PortfolioProject, RightNowPost, RightNowMedia,
    ProjectGallery, WorkExperience, ContentPost, UnifiedJobPreference, LiveOpportunity
)

from profiles.models import (
    Company, CompanyMember, CompanyService, ServiceGalleryImage,
    CompanyMilestone, CompanyNews, NewsGalleryImage, CompanySocialLink, CompanyContactMethod
)

# ==============================================================================
# 1. HIGH-PERFORMANCE MIXINS
# ==============================================================================

class TailwindFormMixin:
    """Injects Tailwind CSS classes securely. Icons cached at class level."""
    ICONS = {
        'mail': "%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' /%3E%3C/svg%3E",
        'link': "%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1' /%3E%3C/svg%3E",
        'calendar': "%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2V7a2 2 0 00-2-2H5a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' /%3E%3C/svg%3E",
        'chevron': "%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M19 9l-7 7-7-7' /%3E%3C/svg%3E",
    }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            widget = field.widget
            base_css = (
                "block w-full bg-slate-50 border border-slate-200 rounded-xl "
                "text-[14.5px] font-medium text-slate-800 placeholder-slate-400 "
                "focus:bg-white focus:border-[#2563EB] focus:ring-4 focus:ring-blue-500/10 "
                "outline-none transition-all duration-200 ease-in-out shadow-sm"
            )
            extra_css = " px-4 py-3.5"

            if isinstance(widget, forms.EmailInput):
                extra_css = f" pl-11 py-3.5 bg-[url('data:image/svg+xml,{self.ICONS['mail']}')] bg-no-repeat bg-[left_1rem_center] bg-[length:1.25rem]"
            elif isinstance(widget, forms.URLInput) or field_name in ['link', 'website', 'url', 'external_link']:
                extra_css = f" pl-11 py-3.5 bg-[url('data:image/svg+xml,{self.ICONS['link']}')] bg-no-repeat bg-[left_1rem_center] bg-[length:1.25rem]"
            elif isinstance(widget, forms.DateInput) or 'date' in field_name:
                extra_css = f" pl-11 py-3.5 bg-[url('data:image/svg+xml,{self.ICONS['calendar']}')] bg-no-repeat bg-[left_1rem_center] bg-[length:1.25rem]"
                widget.attrs['type'] = 'date'
            elif isinstance(widget, forms.Select):
                extra_css = " px-4 py-3.5 appearance-none pr-12 cursor-pointer"
            elif isinstance(widget, forms.Textarea):
                extra_css = " px-4 py-4 min-h-[120px] leading-relaxed resize-y"
            elif isinstance(widget, forms.CheckboxInput):
                base_css = "w-5 h-5 text-[#2563EB] bg-white border-slate-300 rounded focus:ring-[#2563EB] focus:ring-2 cursor-pointer transition-all shrink-0 mt-0.5"
                extra_css = ""
            elif isinstance(widget, (forms.FileInput, forms.ClearableFileInput)):
                base_css = "block w-full text-[13px] text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-[12px] file:font-black file:uppercase file:tracking-widest file:bg-blue-50 file:text-[#2563EB] hover:file:bg-blue-100 transition-all cursor-pointer bg-slate-50 border border-slate-200 rounded-xl p-2"
                extra_css = ""

            existing_classes = widget.attrs.get('class', '')
            widget.attrs['class'] = f"{existing_classes} {base_css} {extra_css}".strip()

class DBRestrictedChoiceFieldsMixin:
    restricted_db_fields = ()
    restricted_model = None
    restricted_source_models = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.restricted_model: return
        for field_name in self.restricted_db_fields:
            field = self.fields.get(field_name)
            if not field: continue
            current_value = self.instance and getattr(self.instance, field_name, None)
            cache_key = f"form_choices_{self.restricted_model.__name__}_{field_name}"
            db_values = cache.get_or_set(cache_key, lambda fn=field_name: self._get_distinct_profile_values(fn), timeout=3600)
            choices_list = list(db_values)
            if current_value and current_value not in choices_list: choices_list.insert(0, current_value)
            choices = [('', _("Select an option"))] + [(val, val) for val in choices_list]
            self.fields[field_name] = forms.TypedChoiceField(choices=choices, required=field.required, coerce=str, empty_value='', label=field.label, help_text=field.help_text, widget=forms.Select(attrs=field.widget.attrs))

    def _get_distinct_profile_values(self, field_name):
        source_model = self.restricted_source_models.get(field_name)
        if source_model:
            queryset = source_model.objects
            if any(field.name == 'is_verified' for field in source_model._meta.fields): queryset = queryset.filter(is_verified=True)
            return list(queryset.exclude(name__isnull=True).exclude(name='').values_list('name', flat=True).distinct().order_by('name')[:1000])
        return list(self.restricted_model.objects.exclude(**{f"{field_name}__isnull": True}).exclude(**{field_name: ''}).values_list(field_name, flat=True).distinct().order_by(field_name)[:1000])


# ==============================================================================
# 2. THE UNIFIED FORMS (HUMAN & INCLUSIVE UX COPY)
# ==============================================================================

class UserProfileForm(TailwindFormMixin, forms.ModelForm):
    full_name = forms.CharField(max_length=150, required=True, label=_("Full Name"))
    email = forms.EmailField(required=False, label=_("Email Address"))
    telegram_handle = forms.CharField(required=False, label=_("Telegram Handle"), widget=forms.TextInput(attrs={'placeholder': '@username'}))

    class Meta:
        model = UserProfile
        fields = ['location', 'institution', 'field_of_interest', 'years_experience', 'bio_narrative', 'cv_file']

        labels = {
            'location': _("Where are you based?"),
            'institution': _("Current Company, Hospital, or University"),
            'field_of_interest': _("Primary Industry or Field"),
            'years_experience': _("Years of Experience"),
            'bio_narrative': _("Your Professional Story"),
            'cv_file': _("Upload Resume or CV (PDF)"),
        }

        help_texts = {
            'location': _("E.g., Addis Ababa, London, San Francisco, or Remote."),
            'institution': _("Where do you currently work, study, or practice?"),
            'field_of_interest': _("E.g., Software Engineering, Public Health, UI/UX Design, Corporate Finance."),
            'bio_narrative': _("Don't just paste your resume! Tell us how you started, what you're passionate about, and what you want to build or achieve next."),
            'cv_file': _("Upload your 1-page CV. Recruiters, startup founders, and clinics look at this first."),
        }

        widgets = {
            'location': forms.TextInput(attrs={'placeholder': _('e.g. Nairobi, Kenya')}),
            'institution': forms.TextInput(attrs={'placeholder': _('e.g. Google, Black Lion Hospital, Safaricom')}),
            'field_of_interest': forms.TextInput(attrs={'placeholder': _('e.g. AI Research or Graphic Design')}),
            'bio_narrative': forms.Textarea(attrs={'placeholder': _('I started my journey when...')}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'user'):
            user = self.instance.user
            self.initial['full_name'] = user.full_name
            self.initial['email'] = user.email
            self.initial['telegram_handle'] = user.telegram_handle

    def clean_cv_file(self):
        cv = self.cleaned_data.get('cv_file')
        if cv and isinstance(cv, UploadedFile):
            if not cv.name.lower().endswith('.pdf'): raise ValidationError(_("CV must be a PDF document."))
            if cv.size > 5 * 1024 * 1024: raise ValidationError(_("CV file size must be under 5MB."))
        return cv


class SkillForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['name', 'proficiency_level', 'status', 'context']

        labels = {
            'name': _("Skill Name"),
            'proficiency_level': _("Your Level"),
            'status': _("Current Status"),
            'context': _("How do you use this skill?"),
        }

        help_texts = {
            'name': _("Add your best strengths (e.g., Python, Patient Care, React.js, Financial Modeling, Video Editing)."),
            'status': _("Are you actively learning this, or do you already use it like a pro?"),
            'context': _("Briefly mention where you applied this. (e.g., 'Used Django to build an API', 'Managed a clinical trial', or 'Designed a brand identity')."),
        }

        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g., Data Analysis'}),
            'context': forms.Textarea(attrs={'placeholder': 'I applied this skill when I was working on...', 'rows': 3}),
        }


class PortfolioProjectForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = PortfolioProject
        fields = ['title', 'context', 'role', 'link', 'problem_statement', 'solution_narrative']

        labels = {
            'title': _("Title of Work"),
            'context': _("Category"),
            'role': _("Your Role"),
            'link': _("Live Link, Publication, or Portfolio"),
            'problem_statement': _("The Goal or Challenge"),
            'solution_narrative': _("Your Approach & Results"),
        }

        help_texts = {
            'title': _("Name of the app, research paper, business plan, or artwork."),
            'role': _("E.g., Lead Full-Stack Engineer, Research Assistant, Sole Designer."),
            'problem_statement': _("What was the main problem you were trying to solve, study, or create?"),
            'solution_narrative': _("How did you do it, and what was the final result or impact?"),
        }

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., CoreLink App or Malaria Prevention Study'}),
            'role': forms.TextInput(attrs={'placeholder': 'e.g., Project Manager'}),
            'problem_statement': forms.Textarea(attrs={'placeholder': 'We needed to find a way to...', 'rows': 3}),
            'solution_narrative': forms.Textarea(attrs={'placeholder': 'I organized a system that resulted in...', 'rows': 4}),
        }


class WorkExperienceForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = WorkExperience
        fields = ['company_name', 'role_title', 'location_type', 'start_date', 'end_date', 'is_current', 'description']

        labels = {
            'company_name': _("Organization Name"),
            'role_title': _("Your Title"),
            'location_type': _("Location Setup"),
            'is_current': _("I currently work here"),
            'description': _("What did you do?"),
        }

        help_texts = {
            'description': _("Highlight your responsibilities and achievements. Don't be humble, tell us your wins! Use bullet points if possible."),
        }

        widgets = {
            'company_name': forms.TextInput(attrs={'placeholder': 'e.g., Microsoft, United Nations, Commercial Bank'}),
            'role_title': forms.TextInput(attrs={'placeholder': 'e.g., Frontend Developer or Logistics Officer'}),
            'description': forms.Textarea(attrs={'placeholder': '• Coordinated supply chain\n• Reduced costs by 15%', 'rows': 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('is_current'): cleaned_data['end_date'] = None
        elif not cleaned_data.get('end_date'): self.add_error('end_date', _("Please provide an end date, or check 'I currently work here'."))
        return cleaned_data


class CredentialForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Credential
        fields = ['credential_type', 'title', 'issuer', 'issue_date', 'url_link', 'file_upload']

        labels = {
            'title': _("Degree or Certificate Name"),
            'issuer': _("Issuing Organization"),
            'issue_date': _("Date Received"),
            'url_link': _("Verification Link"),
            'file_upload': _("Upload Certificate (PDF/Image)"),
        }

        help_texts = {
            'title': _("E.g., AWS Certified Architect, B.Sc. Nursing, Google Data Analytics."),
            'issuer': _("The university, board, or platform (e.g., Coursera, Addis Ababa University)."),
            'url_link': _("Optional link to a digital badge or online publication."),
            'file_upload': _("Upload a scanned copy of your degree or certificate to boost your Trust Score."),
        }

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., Certified Public Accountant (CPA)'}),
            'issuer': forms.TextInput(attrs={'placeholder': 'e.g., Board of Accountancy'}),
        }

    def clean_issue_date(self):
        issue_date = self.cleaned_data.get('issue_date')
        if issue_date and issue_date > date.today(): raise forms.ValidationError(_("Date cannot be in the future."))
        return issue_date


class RightNowPostForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = RightNowPost
        fields = ['title', 'current_search', 'collaboration_status', 'body_narrative', 'external_link', 'is_published']

        labels = {
            'title': _("Catchy Headline"),
            'current_search': _("What are you looking for right now?"),
            'collaboration_status': _("Your Availability"),
            'body_narrative': _("The Details"),
            'external_link': _("Link to your work"),
            'is_published': _("Publish to Global Feed"),
        }

        help_texts = {
            'title': _("E.g., 'Just shipped my first React app!', 'Published a new medical paper', or 'Looking for a design co-founder'."),
            'body_narrative': _("Explain what you're working on or learning. The community loves detailed, authentic updates!"),
            'external_link': _("Paste a link to an article, GitHub repo, or website. We'll generate a beautiful preview!"),
        }

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'What are you focusing on?'}),
            'body_narrative': forms.Textarea(attrs={'placeholder': 'I just spent the weekend studying...', 'rows': 4}),
        }


class ContentPostForm(TailwindFormMixin, forms.ModelForm):
    """Handles the Diary (Growth Logs, Vision Manifestos, Industry Essays)"""
    class Meta:
        model = ContentPost
        fields = ['post_type', 'category', 'title', 'content', 'media_proof', 'visibility']

    def __init__(self, *args, **kwargs):
        self.requested_type = kwargs.pop('post_type', None)
        super().__init__(*args, **kwargs)
        current_type = self.requested_type or (self.instance.post_type if self.instance and self.instance.pk else None)

        # 1. Provide Universal Labels for Visibility
        if 'visibility' in self.fields:
            self.fields['visibility'].label = _("Visibility Status")

        # 2. Shapeshift into a Daily Growth Log
        if current_type == 'GROWTH_LOG':
            self.fields['title'].label = _("What did you learn today?")
            self.fields['content'].label = _("Your Notes")
            self.fields['content'].help_text = _("Jot down your daily learnings, coding bugs you fixed, or study notes. Future you will thank you.")
            if 'visibility' in self.fields:
                self.fields['visibility'].help_text = _("Keep this log private in your diary, or share it on your public profile to show your consistency?")

        # 3. Shapeshift into a Vision Manifesto
        elif current_type == 'VISION_BLOCK':
            self.fields.pop('category', None)
            self.fields.pop('media_proof', None)

            self.fields['title'].label = _("Your Goal")
            self.fields['content'].label = _("Why does this matter?")
            self.fields['content'].help_text = _("Write a long-term vision statement. Where do you see your career or industry heading?")
            if 'visibility' in self.fields:
                self.fields['visibility'].help_text = _("Keep this goal private to stay focused, or share it publicly to attract collaborators who share your vision?")

        # 4. Shapeshift into an Industry Essay
        elif current_type == 'ESSAY':
            self.fields.pop('category', None)
            self.fields.pop('media_proof', None)

            self.fields['title'].label = _("Essay Title")
            self.fields['content'].label = _("Your Thoughts")
            self.fields['content'].help_text = _("Share your deep industry insights, tech tutorials, or personal essays. (Markdown is supported).")
            if 'visibility' in self.fields:
                self.fields['visibility'].help_text = _("Keep this as a private draft while you edit, or publish it publicly to your profile?")

        # Lock the Post Type in the background
        if current_type:
            self.fields['post_type'].widget = forms.HiddenInput()
            self.fields['post_type'].initial = current_type


class LiveOpportunityForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = LiveOpportunity
        fields = ['request_type', 'title', 'details', 'expires_at']

        labels = {
            'request_type': _("What do you need?"),
            'title': _("Headline"),
            'details': _("The Details"),
            'expires_at': _("When does this expire?"),
        }

        help_texts = {
            'title': _("e.g., Seeking a Technical Co-Founder, Looking for a Medical Mentor, Available for Freelance UI Work."),
            'details': _("Provide the exact details, budget, timeline, and what you expect from the other person."),
        }

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., Looking for a Business Partner'}),
            'details': forms.Textarea(attrs={'placeholder': 'I am currently preparing for my exams and need someone to... ', 'rows': 4}),
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class ProfileHeadlineForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = ProfileHeadline
        fields = ['title', 'is_primary']
        labels = {'title': _("Your Professional Headline")}
        help_texts = {'title': _("A short identity (e.g., 'Senior Cloud Architect', 'Medical Student', 'Freelance Writer').")}
        widgets = {'title': forms.TextInput(attrs={'placeholder': 'e.g., Marketing Specialist'})}


class JobPreferenceForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = UnifiedJobPreference
        fields = ['role_title', 'work_arrangement', 'commitment_type', 'description']
        labels = {'role_title': _("Target Role"), 'description': _("What are you looking for?")}


# ==============================================================================
# 4. COMPANY & ADMIN FORMS (Untouched Logic)
# ==============================================================================
class CompanyProfileUpdateForm(DBRestrictedChoiceFieldsMixin, TailwindFormMixin, forms.ModelForm):
    restricted_model = Company
    restricted_db_fields = ('sector', 'location')
    restricted_source_models = {'location': City}
    class Meta:
        model = Company
        fields = ['name', 'sector', 'location', 'operating_since', 'mission_stmt', 'is_hiring', 'looking_for', 'logo', 'cover_image']

class CompanyNewsForm(TailwindFormMixin, forms.ModelForm):
    class Meta: model = CompanyNews; fields = ['title', 'excerpt', 'content', 'cover_image', 'is_published']

class CompanyServiceForm(TailwindFormMixin, forms.ModelForm):
    class Meta: model = CompanyService; fields = ['name', 'description', 'is_active']

class CompanyMilestoneForm(TailwindFormMixin, forms.ModelForm):
    class Meta: model = CompanyMilestone; fields = ['year', 'title', 'description']

class AddCompanyMemberForm(TailwindFormMixin, forms.Form):
    user_identifier = forms.CharField(label=_("User ID or Phone"), widget=forms.TextInput(attrs={'placeholder': 'Search user...'}))
    job_title = forms.CharField(max_length=100)
    role = forms.ChoiceField(choices=CompanyMember.Role.choices, initial=CompanyMember.Role.EDITOR)

# ==============================================================================
# 5. ASSET & GALLERY FORMS
# ==============================================================================
class IdentityMediaForm(forms.ModelForm):
    class Meta: model = CustomUser; fields = ['avatar', 'cover_image']

class SocialLinkForm(TailwindFormMixin, forms.ModelForm):
    class Meta: model = UniversalSocialLink; fields = ['platform_name', 'url', 'icon_slug']; widgets = {'icon_slug': forms.TextInput(attrs={'class': 'hidden'})}

class ContactMethodForm(TailwindFormMixin, forms.ModelForm):
    class Meta: model = UniversalContactMethod; fields = ['type', 'value']

class CompanySocialLinkForm(TailwindFormMixin, forms.ModelForm):
    class Meta: model = CompanySocialLink; fields = ['platform', 'url', 'order']

class CompanyContactMethodForm(TailwindFormMixin, forms.ModelForm):
    class Meta: model = CompanyContactMethod; fields = ['label', 'value']

class ProjectGalleryImageForm(TailwindFormMixin, forms.ModelForm):
    class Meta: model = ProjectGallery; fields = ['image', 'caption']

class ServiceGalleryImageForm(TailwindFormMixin, forms.ModelForm):
    class Meta: model = ServiceGalleryImage; fields = ['image', 'caption']