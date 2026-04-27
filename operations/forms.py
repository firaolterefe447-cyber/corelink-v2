from django import forms
from .models import AchievementClaim


# 1. Styling Mixin
class TailwindFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # CSS Classes
        input_css = "w-full px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:ring-2 focus:ring-slate-900 outline-none transition-all text-sm font-bold text-slate-800 placeholder-slate-400"
        textarea_css = "w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg focus:bg-white focus:ring-2 focus:ring-slate-900 outline-none transition-all text-sm text-slate-600 resize-none placeholder-slate-400"
        file_css = "block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100 transition-all cursor-pointer"

        for field_name, field in self.fields.items():
            w = field.widget

            # Text & URL Inputs
            if isinstance(w, (forms.TextInput, forms.URLInput)):
                w.attrs['class'] = input_css

            # Textareas
            elif isinstance(w, forms.Textarea):
                w.attrs['class'] = textarea_css

            # File & Image Inputs
            elif isinstance(w, (forms.FileInput, forms.ClearableFileInput)):
                w.attrs['class'] = file_css


# 2. The Form Class
class AchievementClaimForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = AchievementClaim
        # CHANGED: 'evidence_link' moved to the end of the list
        fields = ['title', 'description', 'evidence_image', 'evidence_file', 'evidence_link']

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Completed Google UX Certificate'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe what you achieved...'}),
            'evidence_link': forms.URLInput(attrs={'placeholder': 'https://example.com/certificate'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Explicitly set required=False to ensure validation passes without it
        self.fields['evidence_link'].required = False
        self.fields['evidence_file'].required = False
        self.fields['evidence_image'].required = False

        # Update labels to make it clear to the user
        self.fields['evidence_link'].label = "Evidence Link (Optional)"
        self.fields['evidence_file'].label = "Upload Document (Optional)"
        self.fields['evidence_image'].label = "Upload Image (Optional)"