import logging
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import (
    CompanyMessageToAdmin,
    Team,
    TeamMembership,
    PreferenceApplication,
    ConnectionRequest,
    JoinRequest
)

logger = logging.getLogger(__name__)

# ==============================================================================
# TAILWIND MIXIN
# ==============================================================================

class TailwindFormMixin:
    INPUT_CSS = "w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:ring-2 focus:ring-slate-900 focus:border-transparent outline-none transition-all text-sm font-semibold text-slate-800 placeholder-slate-400"
    TEXTAREA_CSS = "w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:ring-2 focus:ring-slate-900 focus:border-transparent outline-none transition-all text-sm text-slate-600 leading-relaxed resize-none"
    SELECT_CSS = "w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:ring-2 focus:ring-slate-900 outline-none text-sm font-bold text-slate-700 cursor-pointer"
    CHECKBOX_CSS = "w-4 h-4 text-slate-900 border-slate-300 rounded focus:ring-slate-900 cursor-pointer"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.TextInput, forms.URLInput, forms.EmailInput, forms.NumberInput, forms.PasswordInput)):
                widget.attrs.update({'class': self.INPUT_CSS})
            elif isinstance(widget, forms.Textarea):
                widget.attrs.update({'class': self.TEXTAREA_CSS})
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.update({'class': self.SELECT_CSS})
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs.update({'class': self.CHECKBOX_CSS})
            elif isinstance(widget, (forms.DateInput, forms.DateTimeInput)):
                widget.attrs.update({'class': self.INPUT_CSS})


# ==============================================================================
# FORMS
# ==============================================================================



class PreferenceApplicationForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = PreferenceApplication
        # REMOVED 'status' because it shouldn't be set by the user in this form
        fields = ['target_role_title', 'seeking', 'preferred_location',
                  'ideal_company_desc', 'value_proposition']
        widgets = {
            'ideal_company_desc': forms.Textarea(attrs={'rows': 4}),
            'value_proposition': forms.Textarea(attrs={'rows': 4}),
        }
class ConnectionRequestForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = ConnectionRequest
        fields = ['title', 'description', 'target_people_description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'target_people_description': forms.Textarea(attrs={'rows': 4}),
        }

class TeamProposalForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'team_type', 'mission', 'roles_needed', 'telegram_link', 'is_recruiting']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': ''}),
            'team_type': forms.Select(),
            'mission': forms.Textarea(attrs={'rows': 4, 'placeholder': ''}),
            'roles_needed': forms.Textarea(attrs={'rows': 3, 'placeholder': ''}),
            'telegram_link': forms.URLInput(attrs={'placeholder': 'https://t.me/...'}),
            'is_recruiting': forms.CheckboxInput(),
        }

class JoinRequestForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = JoinRequest
        fields = ['narrative']
        widgets = {
            'narrative': forms.Textarea(attrs={'rows': 3, 'placeholder': 'I have 3 years of React experience and I love this mission because...'}),
        }



class CompanyMessageForm(forms.ModelForm):
    class Meta:
        model = CompanyMessageToAdmin
        fields = ['title', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({
            'placeholder': 'e.g., Scaling Operations to Europe',
            'class': 'w-full bg-transparent border-b-2 border-slate-200 py-3 text-2xl font-black text-slate-900 outline-none focus:border-slate-900 transition-colors'
        })
        self.fields['description'].widget.attrs.update({
            'placeholder': 'Brain-dump your current friction points, vision, or urgent needs here...',
            'class': 'w-full bg-slate-50 border border-slate-200 rounded-2xl p-6 text-lg font-medium outline-none focus:bg-white focus:border-slate-900 transition-all min-h-[400px] resize-none'
        })