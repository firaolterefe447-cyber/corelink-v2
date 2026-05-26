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
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import date, datetime

logger = logging.getLogger(__name__)

# ==============================================================================
# 0. MODEL IMPORTS
# ==============================================================================
try:
    from accounts.models import CustomUser, UniversalSocialLink, UniversalContactMethod
except ImportError:
    pass

from profiles.models.new_unified_profile import (
    UserProfile, ProfileHeadline, Skill, Credential, PortfolioProject, RightNowPost, RightNowMedia,
    ProjectGallery, WorkExperience, ContentPost, UnifiedJobPreference, LiveOpportunity
)

from profiles.models import (
    Company, CompanyMember, CompanyService, ServiceGalleryImage,
    CompanyMilestone, CompanyNews, NewsGalleryImage, CompanySocialLink, CompanyContactMethod
)

# Standard Date Formats to catch almost any way a user types a date
FLEXIBLE_DATE_FORMATS = [
    '%Y-%m-%d',      # 2026-12-01
    '%m/%d/%Y',      # 12/01/2026
    '%d/%m/%Y',      # 01/12/2026
    '%b %Y',         # Jan 2026
    '%B %Y',         # January 2026
    '%Y-%m',         # 2026-12
]

# ==============================================================================
# 1. HIGH-PERFORMANCE MIXINS
# ==============================================================================

class TailwindFormMixin:
    """Injects Tailwind CSS classes securely. Icons cached at class level."""
    ICONS = {
        'mail': "%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2-2H5a2 2 0 00-2-2H5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' /%3E%3C/svg%3E",
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
                if widget.attrs.get('type') != 'datetime-local' and widget.attrs.get('type') != 'month':
                    widget.attrs['type'] = 'date'
            elif isinstance(widget, forms.Select):
                extra_css = " px-4 py-3.5 appearance-none pr-12 cursor-pointer"
            elif isinstance(widget, forms.RadioSelect):
                base_css = "flex flex-wrap gap-2 radio-pill-group"
                extra_css = ""
            elif isinstance(widget, forms.Textarea):
                extra_css = " px-4 py-4 min-h-[100px] leading-relaxed resize-y"
            elif isinstance(widget, forms.CheckboxInput):
                base_css = "w-5 h-5 text-[#2563EB] bg-white border-slate-300 rounded focus:ring-[#2563EB] focus:ring-2 cursor-pointer transition-all shrink-0 mt-0.5"
                extra_css = ""
            elif isinstance(widget, (forms.FileInput, forms.ClearableFileInput)):
                base_css = "block w-full text-[13px] text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-[12px] file:font-black file:uppercase file:tracking-widest file:bg-blue-50 file:text-[#2563EB] hover:file:bg-blue-100 transition-all cursor-pointer bg-slate-50 border border-slate-200 rounded-xl p-2"
                extra_css = ""

            existing_classes = widget.attrs.get('class', '')
            widget.attrs['class'] = f"{existing_classes} {base_css} {extra_css}".strip()


# ==============================================================================
# 2. THE UNIFIED FORMS
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
            'institution': _("Current Organization / School"),
            'field_of_interest': _("Primary Field or Industry"),
            'years_experience': _("Years of Experience"),
            'bio_narrative': _("Your Professional Story"),
            'cv_file': _("Upload CV (PDF)"),
        }

        help_texts = {
            'location': _("E.g., Addis Ababa, London, San Francisco, or Remote. Type your primary location."),
            'institution': _("Where do you currently work, study, or practice?"),
            'field_of_interest': _("E.g., Agriculture, Healthcare, Education, Engineering, or Business."),
            'years_experience': _("Total number of years you have been active in your field."),
            'bio_narrative': _("Tell us where you started, what you're doing now, and where you want to go. (Markdown supported)"),
            'cv_file': _("Upload your 1-page CV or Resume. This helps others understand your full professional background."),
        }

        widgets = {
            'location': forms.TextInput(attrs={'placeholder': _('e.g. Nairobi, Kenya')}),
            'institution': forms.TextInput(attrs={'placeholder': _('e.g. Safaricom or Addis Ababa University')}),
            'field_of_interest': forms.TextInput(attrs={'placeholder': _('e.g. Healthcare Administration')}),
            'bio_narrative': forms.Textarea(attrs={'placeholder': _('My journey began when...'), 'class': 'markdown-editor'}),
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
    PROFICIENCY_CHOICES = [
        ('JUNIOR', ' Beginner / Still Learning'),
        ('SENIOR', 'Proficient / Use it actively'),
        ('MASTER', ' Expert / Can mentor others'),
    ]
    proficiency_level = forms.ChoiceField(choices=PROFICIENCY_CHOICES, widget=forms.RadioSelect())

    class Meta:
        model = Skill
        fields = ['name', 'proficiency_level', 'context']

        labels = {
            'name': _("Skill / Tool Name"),
            'proficiency_level': _("Proficiency Level"),
            'context': _("How did you use this? (Optional)"),
        }

        help_texts = {
            'name': _("Add a specific skill or tool (e.g., Patient Care, Logistics, Python)."),
            'context': _(
                "Explain how you apply this skill, your experience with it, and your proficiency level. Leave it blank if you want."),
        }

        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g., Supply Chain Management'}),
            'context': forms.Textarea(attrs={'placeholder': 'I applied this skill when I was working on...', 'rows': 2, 'class': 'advanced-field'}),
        }


class PortfolioProjectForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = PortfolioProject
        fields = ['title', 'role', 'link', 'main_description']

        labels = {
            'title': _("Project Title"),
            'role': _("Your Role"),
            'link': _("Live Link or Document (Optional)"),
            'main_description': _("Project Description"),
        }

        help_texts = {
            'title': _(
                "Your project title. E.g., Patient Care Study, Business Plan, Mobile App, or Python Learning Project."),
            'role': _("What did you do? (e.g., Lead Researcher, Developer, or Personal/Learning Project)."),
            'link': _("Optional. A link to see the project live, a document, or a file link."),
            'main_description': _("Explain what the project is, what you did, and what you achieved."),
        }

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., Regional Water Access Study'}),
            'role': forms.TextInput(attrs={'placeholder': 'e.g., Operations Lead'}),
            'main_description': forms.Textarea(attrs={'placeholder': 'Describe your project ....', 'rows': 5, 'class': 'markdown-editor'}),
        }


class WorkExperienceForm(TailwindFormMixin, forms.ModelForm):
    # Updated to handle robust standard dates
    start_date = forms.DateField(
        input_formats=FLEXIBLE_DATE_FORMATS,
        widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'MM/DD/YYYY'}),
        help_text=_("Select a date from the calendar, or type it as MM/DD/YYYY (e.g. 12/01/2026).")
    )
    end_date = forms.DateField(
        input_formats=FLEXIBLE_DATE_FORMATS,
        widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'MM/DD/YYYY'}),
        required=False,
        help_text=_("Leave blank if this is your current role.")
    )

    class Meta:
        model = WorkExperience
        fields = ['company_name', 'role_title', 'location_type', 'start_date', 'end_date', 'is_current', 'description']

        labels = {
            'company_name': _("Organization Name"),
            'role_title': _("Your Title"),
            'location_type': _("Location Setup"),
            'start_date': _("Start Date"),
            'end_date': _("End Date"),
            'is_current': _("I currently work here"),
            'description': _("Role Description"),
        }

        help_texts = {
            'company_name': _("The name of the company, hospital, organization, or school where you worked."),
            'role_title': _("Your job title (e.g., Lead Developer, Graphics Designer, Medical Officer, or Intern)."),
            'location_type': _("Select whether you worked on-site, remotely, or in a hybrid setup."),
            'description': _("Explain your daily tasks, responsibilities, and achievements."),
        }

        widgets = {
            'company_name': forms.TextInput(attrs={'placeholder': 'e.g., Ministry of Health, Commercial Bank'}),
            'role_title': forms.TextInput(attrs={'placeholder': 'e.g., Logistics Officer or Clinic Supervisor'}),
            'location_type': forms.RadioSelect(),
            'description': forms.Textarea(attrs={'placeholder': '• Coordinated daily operations\n• Managed a team of 15 staff members', 'rows': 4}),
        }

    def clean(self):
        cleaned_data = super().clean()

        # Ensure we properly handle the fallback if a user types a weird date format
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        is_current = cleaned_data.get('is_current')

        if is_current:
            cleaned_data['end_date'] = None
        elif not end_date:
            self.add_error('end_date', _("Please provide an end date, or check 'I currently work here'."))

        if start_date and end_date and start_date > end_date:
            self.add_error('end_date', _("End date cannot be earlier than the start date."))

        return cleaned_data


class CredentialForm(TailwindFormMixin, forms.ModelForm):
    # Updated to handle robust standard dates
    issue_date = forms.DateField(
        input_formats=FLEXIBLE_DATE_FORMATS,
        widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'MM/DD/YYYY'}),
        required=False,
        help_text=_("Select a date from the calendar, or type it as MM/DD/YYYY (e.g. 12/01/2026).")
    )

    class Meta:
        model = Credential
        fields = ['title', 'issuer', 'issue_date', 'reflection', 'url_link', 'file_upload']

        labels = {
            'title': _("Degree or Certificate Name"),
            'issuer': _("Issuing Organization"),
            'issue_date': _("Date Received"),
            'reflection': _("Description / What did you learn?"),
            'url_link': _("Verification Link (Optional)"),
            'file_upload': _("Upload Certificate (PDF/Image)"),
        }

        help_texts = {
            'title': _("E.g., Bachelor in Computer Science, Foundations of AI, or Graphics Design."),
            'issuer': _("The school, online platform, organization, or community that gave you this certificate."),
            'reflection': _("Optional. Share what you learned or how this certificate helped you grow."),
            'url_link': _(
                "Optional. A link to the online certificate, badge, or proof of achievement if you have one."),
            'file_upload': _("Upload a picture or PDF of your certificate to show your proof of work."),
        }

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., Master of Business Administration (MBA)'}),
            'issuer': forms.TextInput(attrs={'placeholder': 'e.g., Addis Ababa University'}),
            'reflection': forms.Textarea(attrs={'placeholder': 'This certification covered...', 'rows': 3, 'class': 'advanced-field'}),
        }

    def clean_issue_date(self):
        issue_date = self.cleaned_data.get('issue_date')
        if issue_date and issue_date > date.today():
            raise forms.ValidationError(_("Date cannot be in the future."))
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
            'current_search': _("What is your primary goal right now?"),
            'collaboration_status': _("Are you currently open to new opportunities, hiring, or seeking partners?"),
            'body_narrative': _("Provide the details of your current work or learning focus. Clear updates help others understand how to collaborate with you."),
            'external_link': _("Include a link to an article, document, or website related to your update."),
        }

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'What are you currently focusing on?'}),
            'current_search': forms.Select(attrs={'class': 'w-full'}),
            'collaboration_status': forms.Select(attrs={'class': 'w-full'}),
            'body_narrative': forms.Textarea(attrs={'placeholder': 'I have recently been working on...', 'rows': 4}),
        }


class ContentPostForm(TailwindFormMixin, forms.ModelForm):
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
            self.fields['title'].help_text = _("Give your log a quick title (e.g., 'Week 1 of Project Deployment').")
            self.fields['content'].label = _("Notes & Observations")
            self.fields['content'].help_text = _("A place to document your daily progress, challenges overcome, or important notes.")
            self.fields['content'].widget.attrs.update({'class': 'markdown-editor', 'placeholder': 'Today I learned...'})

        elif current_type == 'VISION_BLOCK':
            self.fields.pop('category', None)
            self.fields.pop('media_proof', None)

            self.fields['title'].label = _("Vision or Goal")
            self.fields['title'].help_text = _("Give title you want for your goal ? (e.g., 'My 5 year plan').")
            self.fields['content'].label = _("Detailed Plan")
            self.fields['content'].help_text = _("Outline a long-term goal. Where do you see your career or industry heading in the future?")
            self.fields['content'].widget.attrs.update({'class': 'markdown-editor', 'placeholder': 'Eplain here'})

        elif current_type == 'ESSAY':
            self.fields.pop('category', None)
            self.fields.pop('media_proof', None)

            self.fields['title'].label = _("Article Title")
            self.fields['title'].help_text = _("An engaging headline for your article or thought-leadership post.")
            self.fields['content'].label = _("Article Content")
            self.fields['content'].help_text = _("Share your professional insights, write an essay, or publish a detailed guide. Markdown formatting is supported.")
            self.fields['content'].widget.attrs.update({'class': 'markdown-editor min-h-[300px]', 'placeholder': 'Start writing...'})

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
            'request_type': _("Categorize the type of opportunity you are posting."),
            'title': _("E.g., Seeking an Agricultural Consultant, Looking for a Study Partner, Available for Accounting Consultation."),
            'details': _("Provide clear details regarding expectations, timelines, and the type of collaboration you are seeking."),
            'expires_at': _("When should this opportunity be automatically removed from the live feed?"),
        }

        widgets = {
            'request_type': forms.RadioSelect(),
            'title': forms.TextInput(attrs={'placeholder': 'e.g., Looking for a Logistics Expert'}),
            'details': forms.Textarea(attrs={'placeholder': 'I am currently organizing a project and require someone who can...', 'rows': 4}),
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class ProfileHeadlineForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = ProfileHeadline
        fields = ['title', 'is_primary']
        labels = {
            'title': _("Your Professional Headline"),
            'is_primary': _("Set as Primary Headline"),
        }
        help_texts = {
            'title': _("A short description of your primary role (e.g., 'Hospital Administrator', 'Civil Engineer', 'Retail Manager')."),
            'is_primary': _("Check this to display this headline prominently at the top of your profile."),
        }
        widgets = {'title': forms.TextInput(attrs={'placeholder': 'e.g., Operations Manager'})}


class JobPreferenceForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = UnifiedJobPreference
        fields = ['role_title', 'work_arrangement', 'commitment_type', 'description']

        labels = {
            'role_title': _("Target Role"),
            'work_arrangement': _("Preferred Setup"),
            'commitment_type': _("Commitment Level"),
            'description': _("What are you looking for?")
        }

        help_texts = {
            'role_title': _("The specific job title you are aiming for (e.g., 'Senior Accountant' or 'Lead Developer')."),
            'work_arrangement': _("Do you prefer working remotely, on-site at an office, or hybrid?"),
            'commitment_type': _("Are you seeking full-time, part-time, or contract-based opportunities?"),
            'description': _("Describe the type of work environment, team culture, or industry challenges you want to tackle."),
        }


# ==============================================================================
# 4. COMPANY & ADMIN FORMS (UNIVERSAL & PROFESSIONAL)
# ==============================================================================

class CompanyProfileUpdateForm(TailwindFormMixin, forms.ModelForm):
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
            'sector': _("E.g., Agriculture, Manufacturing, Healthcare, Retail. Type the industry that best describes your core business."),
            'location': _("E.g., Addis Ababa, Nairobi, London, or Remote. Type the city and country where your primary operations are based."),
            'operating_since': _("The year the business was officially founded or established."),
            'mission_stmt': _("Write a deep description of your business identity and core mission. Share your authentic story and the values that make your company unique"),
            'is_hiring': _("Check this box if your company currently has open job positions."),
            'looking_for': _("Select your primary business objective to help others in the network understand how they can collaborate with you."),
        }

        widgets = {
            'sector': forms.TextInput(attrs={'placeholder': 'e.g. Healthcare Technology'}),
            'location': forms.TextInput(attrs={'placeholder': 'e.g. Addis Ababa, Ethiopia'}),
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
            'content': forms.Textarea(attrs={'rows': 8, 'placeholder': 'Provide the full details here...', 'class': 'markdown-editor'}),
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
            'description': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Explain your service or product in detial ...'}),
        }


class CompanyMilestoneForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = CompanyMilestone
        fields = ['year', 'title', 'description']

        labels = {
            'year': _("Year "),
            'title': _("Milestone Title"),
            'description': _("Details"),
        }

        help_texts = {
            'year': _("The year this event occurred."),
            'title': _("A short headline (e.g., 'we founded X company ' 'Opened New Branch', 'Reached 100 Employees', 'Launched New Product Line')."),
            'description': _("Share details about this achievement and how it helped your organization grow."),
        }

        widgets = {
            'year': forms.NumberInput(attrs={'placeholder': 'e.g. 2022'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Eplain the event...'}),
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
    class Meta:
        model = CustomUser
        fields = ['avatar', 'cover_image']

        labels = {
            'avatar': _("Profile Photo"),
            'cover_image': _("Cover Image"),
        }

        help_texts = {
            'avatar': _("Upload a clear, professional headshot. This is the first thing people see when they visit your profile."),
            'cover_image': _("Upload a wide background banner for your profile. This helps customize your page's visual appearance."),
        }


class SocialLinkForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = UniversalSocialLink
        fields = ['platform_name', 'url', 'icon_slug']

        labels = {
            'platform_name': _("Platform Name"),
            'url': _("Profile URL"),
        }

        help_texts = {
            'platform_name': _("E.g., LinkedIn, Twitter, GitHub, or Personal Website."),
            'url': _("Paste the full web address to your profile (e.g., https://linkedin.com/in/username)."),
        }

        widgets = {'icon_slug': forms.TextInput(attrs={'class': 'hidden'})}


class ContactMethodForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = UniversalContactMethod
        fields = ['type', 'value']

        labels = {
            'type': _("Contact Type"),
            'value': _("Contact Detail"),
        }

        help_texts = {
            'type': _("Select the type of contact method (e.g., Email, Phone Number, WhatsApp)."),
            'value': _("Enter the actual email address, phone number, or username."),
        }


class CompanySocialLinkForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = CompanySocialLink
        fields = ['platform', 'url', 'order']

        labels = {
            'platform': _("Platform"),
            'url': _("Profile URL"),
            'order': _("Display Order"),
        }

        help_texts = {
            'platform': _("The social media network or website (e.g.,our official website, LinkedIn, Facebook, X/Twitter)."),
            'url': _("The direct web link to your company's official page."),
            'order': _("Set the sequence in which this link appears. Lower numbers show up first."),
        }


class CompanyContactMethodForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = CompanyContactMethod
        fields = ['label', 'value']

        labels = {
            'label': _("Contact Label"),
            'value': _("Contact Details"),
        }

        help_texts = {
            'label': _("A clear name for this contact method (e.g., 'Sales Desk', 'Support Email', 'Main Office')."),
            'value': _("The actual phone number, email address, or physical address clients should use."),
        }


class ProjectGalleryImageForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = ProjectGallery
        fields = ['image', 'caption']

        labels = {
            'image': _("Upload Image"),
            'caption': _("Image Caption"),
        }

        help_texts = {
            'image': _("Upload a high-quality image demonstrating your project or work."),
            'caption': _("A brief description of what this image shows (e.g., 'Final Dashboard UI' or 'Field Operation Day 1')."),
        }


class ServiceGalleryImageForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = ServiceGalleryImage
        fields = ['image', 'caption']

        labels = {
            'image': _("Upload Image"),
            'caption': _("Image Caption"),
        }

        help_texts = {
            'image': _("Upload a clear photo representing this product or service."),
            'caption': _("A brief description highlighting what customers are looking at."),
        }