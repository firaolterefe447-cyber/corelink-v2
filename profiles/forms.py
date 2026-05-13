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
        'mail': "%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2-2H5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' /%3E%3C/svg%3E",
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
            'field_of_interest': _("E.g., Agriculture, Healthcare, Education, Engineering, or Business."),
            'bio_narrative': _("Provide a detailed professional biography. Tell us about your background, your current work, and your future goals."),
            'cv_file': _("Upload your 1-page CV or Resume. This helps others understand your full professional background."),
        }

        widgets = {
            'location': forms.TextInput(attrs={'placeholder': _('e.g. Nairobi, Kenya')}),
            'institution': forms.TextInput(attrs={'placeholder': _('e.g. Black Lion Hospital, Safaricom, or Addis Ababa University')}),
            'field_of_interest': forms.TextInput(attrs={'placeholder': _('e.g. Healthcare Administration or Civil Engineering')}),
            'bio_narrative': forms.Textarea(attrs={'placeholder': _('I began my career in...')}),
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
            'name': _("Add a specific skill or strength (e.g., Patient Care, Logistics Management, Python, Financial Modeling, Graphic Design)."),
            'status': _("Indicate whether you are currently learning this, or if you already use it professionally."),
            'context': _("Briefly mention where you applied this skill (e.g., 'Managed inventory for a retail branch', or 'Used for daily patient reporting')."),
        }

        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g., Supply Chain Management'}),
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
            'link': _("Live Link, Publication, or Document"),
            'problem_statement': _("The Goal or Challenge"),
            'solution_narrative': _("Your Approach & Results"),
        }

        help_texts = {
            'title': _("The name of the project, research paper, business plan, or campaign."),
            'role': _("Your specific position during this work (e.g., Project Manager, Research Assistant, Lead Technician)."),
            'problem_statement': _("Explain the main objective or the problem you were trying to solve."),
            'solution_narrative': _("Describe the steps you took and the final outcome or impact of the work."),
        }

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., Regional Water Access Study or Store Expansion Project'}),
            'role': forms.TextInput(attrs={'placeholder': 'e.g., Operations Lead'}),
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
            'description': _("Role Description"),
        }

        help_texts = {
            'description': _("Highlight your key responsibilities and professional achievements. Using bullet points makes it easier to read."),
        }

        widgets = {
            'company_name': forms.TextInput(attrs={'placeholder': 'e.g., Ministry of Health, Commercial Bank, United Nations'}),
            'role_title': forms.TextInput(attrs={'placeholder': 'e.g., Logistics Officer or Clinic Supervisor'}),
            'description': forms.Textarea(attrs={'placeholder': '• Coordinated daily operations\n• Managed a team of 15 staff members', 'rows': 4}),
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
            'title': _("E.g., B.Sc. Nursing, Certified Public Accountant, or Project Management Professional."),
            'issuer': _("The university, licensing board, or training organization."),
            'url_link': _("An optional web link to verify the credential digitally."),
            'file_upload': _("Upload a clear copy of your degree or certificate to improve your profile verification."),
        }

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., Master of Business Administration (MBA)'}),
            'issuer': forms.TextInput(attrs={'placeholder': 'e.g., Addis Ababa University'}),
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
            'title': _("Update Title"),
            'current_search': _("Current Objective"),
            'collaboration_status': _("Your Availability"),
            'body_narrative': _("Details"),
            'external_link': _("External Link"),
            'is_published': _("Publish to Global Feed"),
        }

        help_texts = {
            'title': _("E.g., 'Completed a major supply chain project', 'Published a new research paper', or 'Looking for a business partner'."),
            'body_narrative': _("Provide the details of your current work or learning focus. Clear updates help others understand how to collaborate with you."),
            'external_link': _("Include a link to an article, document, or website related to your update."),
        }

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'What are you currently focusing on?'}),
            'body_narrative': forms.Textarea(attrs={'placeholder': 'I have recently been working on...', 'rows': 4}),
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

        if 'visibility' in self.fields:
            self.fields['visibility'].label = _("Visibility Status")

        if current_type == 'GROWTH_LOG':
            self.fields['title'].label = _("Entry Title")
            self.fields['content'].label = _("Notes & Observations")
            self.fields['content'].help_text = _("A place to document your daily progress, challenges overcome, or important notes.")
            if 'visibility' in self.fields:
                self.fields['visibility'].help_text = _("Keep this log private for your own records, or share it on your profile.")

        elif current_type == 'VISION_BLOCK':
            self.fields.pop('category', None)
            self.fields.pop('media_proof', None)

            self.fields['title'].label = _("Vision or Goal")
            self.fields['content'].label = _("Detailed Plan")
            self.fields['content'].help_text = _("Outline a long-term goal. Where do you see your career or industry heading in the future?")
            if 'visibility' in self.fields:
                self.fields['visibility'].help_text = _("Keep this private to stay focused, or publish it to connect with others who share similar goals.")

        elif current_type == 'ESSAY':
            self.fields.pop('category', None)
            self.fields.pop('media_proof', None)

            self.fields['title'].label = _("Article Title")
            self.fields['content'].label = _("Article Content")
            self.fields['content'].help_text = _("Share your professional insights, write an essay, or publish a detailed guide. Markdown formatting is supported.")
            if 'visibility' in self.fields:
                self.fields['visibility'].help_text = _("Keep this as a private draft while writing, or publish it to your profile.")

        if current_type:
            self.fields['post_type'].widget = forms.HiddenInput()
            self.fields['post_type'].initial = current_type


class LiveOpportunityForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = LiveOpportunity
        fields = ['request_type', 'title', 'details', 'expires_at']

        labels = {
            'request_type': _("Type of Request"),
            'title': _("Headline"),
            'details': _("Full Details"),
            'expires_at': _("Expiration Date"),
        }

        help_texts = {
            'title': _("E.g., Seeking an Agricultural Consultant, Looking for a Study Partner, Available for Accounting Consultation."),
            'details': _("Provide clear details regarding expectations, timelines, and the type of collaboration you are seeking."),
        }

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., Looking for a Logistics Expert'}),
            'details': forms.Textarea(attrs={'placeholder': 'I am currently organizing a project and require someone who can...', 'rows': 4}),
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class ProfileHeadlineForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = ProfileHeadline
        fields = ['title', 'is_primary']
        labels = {'title': _("Your Professional Headline")}
        help_texts = {'title': _("A short description of your primary role (e.g., 'Hospital Administrator', 'Civil Engineer', 'Retail Manager').")}
        widgets = {'title': forms.TextInput(attrs={'placeholder': 'e.g., Operations Manager'})}


class JobPreferenceForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = UnifiedJobPreference
        fields = ['role_title', 'work_arrangement', 'commitment_type', 'description']
        labels = {'role_title': _("Target Role"), 'description': _("What are you looking for?")}


# ==============================================================================
# 4. COMPANY & ADMIN FORMS (UNIVERSAL & PROFESSIONAL)
# ==============================================================================

class CompanyProfileUpdateForm(DBRestrictedChoiceFieldsMixin, TailwindFormMixin, forms.ModelForm):
    restricted_model = Company
    restricted_db_fields = ('sector', 'location')
    restricted_source_models = {'location': City}

    class Meta:
        model = Company
        fields = ['name', 'sector', 'location', 'operating_since', 'mission_stmt', 'is_hiring', 'looking_for']

        labels = {
            'name': _("Company Name"),
            'sector': _("Industry / Sector"),
            'location': _("Headquarters Location"),
            'operating_since': _("Year Established"),
            'mission_stmt': _("About the Company"),
            'is_hiring': _("Currently Hiring"),
            'looking_for': _("Primary Objective"),
        }

        help_texts = {
            'name': _("The official registered or trading name of your business or organization."),
            'sector': _("E.g., Agriculture, Manufacturing, Healthcare, Retail, Education, or Finance."),
            'location': _("The city and country where your primary operations or headquarters are located."),
            'operating_since': _("The year the business was officially founded or established."),
            'mission_stmt': _("Describe your business, the services you provide, and the customers you serve. Share your history and what makes your company unique."),
            'is_hiring': _("Check this box if your company currently has open job positions."),
            'looking_for': _("Select your primary business objective to help others in the network understand how they can collaborate with you."),
        }

        widgets = {
            'mission_stmt': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Our organization was founded to provide...'}),
            'operating_since': forms.NumberInput(attrs={'placeholder': 'e.g. 2015'}),
        }

class CompanyNewsForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = CompanyNews
        fields = ['title', 'excerpt', 'content', 'is_published']

        labels = {
            'title': _("News Headline"),
            'excerpt': _("Short Summary"),
            'content': _("Full Article"),
            'is_published': _("Publish Immediately"),
        }

        help_texts = {
            'title': _("The title of your announcement, event summary, or press release."),
            'excerpt': _("A brief summary of your announcement. This appears as a preview before people click to read the full article."),
            'content': _("The full details of your news or update. You can use formatting to create a clear and professional article."),
            'is_published': _("Uncheck this box if you wish to save the article as a draft to review later."),
        }

        widgets = {
            'excerpt': forms.Textarea(attrs={'rows': 2, 'placeholder': 'A brief overview of the announcement...'}),
            'content': forms.Textarea(attrs={'rows': 8, 'placeholder': 'Provide the full details here...'}),
        }

class CompanyServiceForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = CompanyService
        fields = ['name', 'description', 'is_active']

        labels = {
            'name': _("Product or Service Name"),
            'description': _("Description"),
            'is_active': _("Currently Available"),
        }

        help_texts = {
            'name': _("The name of the specific product, good, or service you provide."),
            'description': _("Explain what this offering is, who your target customers are, and the value it brings to them."),
            'is_active': _("Uncheck this box if you no longer provide this product or service."),
        }

        widgets = {
            'description': forms.Textarea(attrs={'rows': 5, 'placeholder': 'This service is designed to help customers...'}),
        }

class CompanyMilestoneForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = CompanyMilestone
        fields = ['year', 'title', 'description']

        labels = {
            'year': _("Year Achieved"),
            'title': _("Milestone Title"),
            'description': _("Details"),
        }

        help_texts = {
            'year': _("The year this event occurred."),
            'title': _("A short headline (e.g., 'Opened New Branch', 'Reached 100 Employees', 'Launched New Product Line')."),
            'description': _("Share details about this achievement and how it helped your organization grow."),
        }

        widgets = {
            'year': forms.NumberInput(attrs={'placeholder': 'e.g. 2022'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'This milestone allowed the organization to...'}),
        }

class AddCompanyMemberForm(TailwindFormMixin, forms.Form):
    user_identifier = forms.CharField(label=_("Search User"), widget=forms.TextInput(attrs={'placeholder': 'Enter Email or Phone number...'}))
    job_title = forms.CharField(max_length=100, label=_("Job Title"), help_text=_("The person's official role within the organization (e.g., 'Operations Manager' or 'Senior Accountant')."))
    role = forms.ChoiceField(
        choices=CompanyMember.Role.choices,
        initial=CompanyMember.Role.EDITOR,
        label=_("Permissions Level"),
        help_text=_("Admins have full access to settings. Editors can only write news articles and update services.")
    )


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