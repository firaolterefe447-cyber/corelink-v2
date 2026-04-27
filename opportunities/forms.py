# opportunities/forms.py

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import JobPost
from profiles.models import CompanyMember


class OpportunitySubmissionForm(forms.ModelForm):
    """
    The Master Form for creating Opportunities.
    Handles: Internal Jobs, Challenges, and External Posts.
    """
    post_as = forms.ChoiceField(
        label=_("Post As"),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = JobPost
        fields =[
            # Core
            'title', 'job_type', 'level', 'cover_image', 'description',
            'is_remote', 'location', 'required_skills',

            # Financials
            'compensation_text', 'salary_min', 'salary_max',

            # Deadlines
            'deadline_date', 'deadline_text', 'is_open_ended',

            # Challenge Mode (CoreLink Innovation)
            'requires_challenge', 'challenge_description',

            # External Links
            'is_external', 'external_url', 'external_company_name', 'external_company_logo',
        ]
        widgets = {
            'level': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Describe the mission, requirements, and impact...',
                'class': 'form-control'
            }),
            'challenge_description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'E.g. Attach a GitHub repo where you built a REST API or a Figma link to a landing page design...',
                'class': 'form-control'
            }),
            # Deadline Widgets
            'deadline_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'deadline_text': forms.TextInput(attrs={
                'placeholder': "e.g., 'Rolling basis', 'End of Month', 'Apply ASAP'",
                'class': 'form-control'
            }),
            'required_skills': forms.SelectMultiple(attrs={
                'class': 'select2-multiple form-control'
            }),
            'is_external': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_remote': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_open_ended': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_challenge': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'is_external': _('Check this if candidates should apply on an outside website (e.g., Google Forms, LinkedIn).'),
            'is_open_ended': _('Check this if the role is open until filled.'),
            'requires_challenge': _('Bypass resumes. Require candidates to attach a specific Project/Proof of Work to apply.'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # 1. Mark fields as optional in the UI (Django's clean() method will handle strict logic)
        optional_fields =[
            'cover_image', 'location', 'compensation_text', 'is_remote',
            'salary_min', 'salary_max', 'challenge_description',
            'external_url', 'external_company_name', 'external_company_logo',
            'deadline_date', 'deadline_text'
        ]
        for field in optional_fields:
            self.fields[field].required = False

        # 2. Build Attribution Choices dynamically based on user context
        choices =[]
        valid_memberships = None # Initialized as None to prevent list .exists() crash

        if self.user:
            valid_memberships = CompanyMember.objects.filter(
                user=self.user,
                role__in=['OWNER', 'ADMIN'],
                is_active=True
            ).select_related('company')

            # PRIORITY 1: Companies (Top)
            for membership in valid_memberships:
                choices.append((f"COMPANY_{membership.company.id}", f"🏢 {membership.company.name}"))

            # PRIORITY 2: Personal Identity
            user_name = self.user.get_full_name() or self.user.username
            choices.append(('USER', f'👤 Myself ({user_name})'))

            # PRIORITY 3: Admin Post
            is_admin = getattr(self.user, 'role', None) == 'ADMIN' or self.user.is_staff
            if is_admin:
                choices.append(('OFFICIAL_ADMIN', '🌟 Official Core Admin Post'))

        self.fields['post_as'].choices = choices

        # 3. Set Initial Value Safely
        if self.instance and self.instance.pk:
            if self.instance.is_official_admin_post:
                self.initial['post_as'] = 'OFFICIAL_ADMIN'
            elif self.instance.company:
                self.initial['post_as'] = f"COMPANY_{self.instance.company.id}"
            else:
                self.initial['post_as'] = 'USER'
        else:
            # Safely check if valid_memberships is a QuerySet and exists
            if valid_memberships and valid_memberships.exists():
                self.initial['post_as'] = f"COMPANY_{valid_memberships.first().company.id}"
            else:
                self.initial['post_as'] = 'USER'

    def clean(self):
        cleaned_data = super().clean()

        # 1. Removed External Job URL Validation to allow external posts without mandatory URLs

        # -----------------------------------------------------------------
        # 2. SMOOTH 3-WAY DEADLINE LOGIC (Zero-Friction Fix)
        # -----------------------------------------------------------------
        is_open_ended = cleaned_data.get('is_open_ended')
        deadline_date = cleaned_data.get('deadline_date')
        deadline_text = cleaned_data.get('deadline_text')

        # If they left Date and Text blank, and didn't check open-ended
        if not deadline_date and not deadline_text and not is_open_ended:
            # Silently auto-correct it to Open-Ended so they can keep moving.
            cleaned_data['is_open_ended'] = True

        # If they picked a date OR wrote custom text, ensure open-ended is strictly False
        elif deadline_date or deadline_text:
            cleaned_data['is_open_ended'] = False

        # 3. Challenge Validation
        requires_challenge = cleaned_data.get('requires_challenge')
        challenge_description = cleaned_data.get('challenge_description')
        if requires_challenge and not challenge_description:
            self.add_error('challenge_description', _("Please describe the challenge requirements."))

        # 4. Salary Bound Validation
        salary_min = cleaned_data.get('salary_min')
        salary_max = cleaned_data.get('salary_max')
        if salary_min and salary_max and salary_min > salary_max:
            self.add_error('salary_min', _("Minimum salary cannot be greater than maximum salary."))

        return cleaned_data


class OpportunitySearchForm(forms.Form):
    """
    Smart, AI-ready search form used by the Feed View.
    """
    DATE_CHOICES =[
        ('', '📅 Any Time'),
        ('1', 'Last 24 Hours'),
        ('7', 'Last 7 Days'),
        ('30', 'Last 30 Days'),
    ]

    q = forms.CharField(
        required=False,
        label='Smart Search',
        widget=forms.TextInput(attrs={
            'placeholder': '🔍 Search title, skill, or company...',
            'class': 'form-control form-control-lg border-0 shadow-sm ps-4 rounded-pill',
            'style': 'background-color: #f8f9fa;'
        })
    )

    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': '📍 City or "Remote"',
            'class': 'form-control border-0 shadow-sm rounded-pill',
            'style': 'background-color: #f8f9fa;'
        })
    )

    # CoreLink Innovation: Allow users to filter specifically for Challenge-based jobs!
    requires_challenge = forms.BooleanField(
        required=False,
        label=_("🏆 Challenge Mode Only"),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input shadow-sm cursor-pointer'
        })
    )

    is_remote = forms.BooleanField(
        required=False,
        label=_("🌐 Remote Only"),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input shadow-sm cursor-pointer'
        })
    )

    job_type = forms.ChoiceField(
        choices=[('', '💼 All Job Types')] + JobPost.JobType.choices,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select border-0 shadow-sm rounded-pill',
            'style': 'background-color: #f8f9fa; cursor: pointer;'
        })
    )

    level = forms.ChoiceField(
        choices=[('', '🎓 All Levels')] + JobPost.ExperienceLevel.choices,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select border-0 shadow-sm rounded-pill',
            'style': 'background-color: #f8f9fa; cursor: pointer;'
        })
    )

    days_posted = forms.ChoiceField(
        choices=DATE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select border-0 shadow-sm rounded-pill',
            'style': 'background-color: #f8f9fa; cursor: pointer;'
        })
    )

    def clean_q(self):
        return self.cleaned_data.get('q', '').strip()


class PublicOpportunitySubmissionForm(forms.ModelForm):
    """
    Guest Form for creating Opportunities.
    Functions exactly like the internal form, but requires contact info and an external link.
    """
    submitter_contact = forms.CharField(
        label=_("Your Contact Info (For Admin Use)"),
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., @Abebe_Kebede on Telegram, Phone, or Email...'
        }),
        help_text=_("We need this to let you know when your post goes live. It will NOT be public.")
    )

    class Meta:
        model = JobPost
        fields = [
            # Exact same fields as internal form
            'title', 'job_type', 'level', 'cover_image', 'description',
            'is_remote', 'location', 'required_skills',
            'compensation_text', 'salary_min', 'salary_max',
            'deadline_date', 'deadline_text', 'is_open_ended',
            'requires_challenge', 'challenge_description',

            # External Links (Mandatory for Guests)
            'external_url', 'external_company_name', 'external_company_logo',
        ]

        # Use the exact same widgets as OpportunitySubmissionForm for UI consistency
        widgets = {
            'level': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(
                attrs={'rows': 5, 'class': 'form-control', 'placeholder': 'Describe the mission...'}),
            'challenge_description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'deadline_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'deadline_text': forms.TextInput(attrs={'class': 'form-control'}),
            'required_skills': forms.SelectMultiple(attrs={'class': 'select2-multiple form-control'}),
            'is_remote': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_open_ended': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_challenge': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'external_url': forms.URLInput(
                attrs={'class': 'form-control', 'placeholder': 'Google Form, Telegram link, Website...'}),
            'external_company_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make certain fields optional just like the master form
        optional_fields = [
            'cover_image', 'location', 'compensation_text', 'is_remote',
            'salary_min', 'salary_max', 'challenge_description',
            'external_company_logo', 'deadline_date', 'deadline_text'
        ]
        for field in optional_fields:
            self.fields[field].required = False

        # Guests MUST provide an external URL and Company name because they don't have a dashboard
        self.fields['external_url'].required = True
        self.fields['external_company_name'].required = True

    def clean(self):
        cleaned_data = super().clean()

        # 1. 3-Way Deadline Logic (Copied exactly from master form)
        is_open_ended = cleaned_data.get('is_open_ended')
        deadline_date = cleaned_data.get('deadline_date')
        deadline_text = cleaned_data.get('deadline_text')

        if not deadline_date and not deadline_text and not is_open_ended:
            cleaned_data['is_open_ended'] = True
        elif deadline_date or deadline_text:
            cleaned_data['is_open_ended'] = False

        # 2. Challenge Validation (Copied exactly)
        requires_challenge = cleaned_data.get('requires_challenge')
        challenge_description = cleaned_data.get('challenge_description')
        if requires_challenge and not challenge_description:
            self.add_error('challenge_description', _("Please describe the challenge requirements."))

        # 3. Force Guest Posts to be External (Crucial!)
        # We manually inject this because guests don't have the checkbox
        cleaned_data['is_external'] = True

        return cleaned_data