from django import forms
from .models import NetworkPost


class NetworkPostForm(forms.ModelForm):
    class Meta:
        model = NetworkPost
        fields = [
            'headline', 'description', 'project_type',
            'project_stage', 'need_type', 'looking_for'
        ]
        widgets = {
            'headline': forms.TextInput(attrs={
                'class': 'w-full bg-white border border-[#E2E8F0] rounded-xl px-4 py-3 text-[#0F172A] focus:border-[#0A66C2] focus:ring-1 focus:ring-[#0A66C2] outline-none transition-all placeholder:text-[#94A3B8]',
                'placeholder': 'A concise, professional title for the work'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full bg-white border border-[#E2E8F0] rounded-xl px-4 py-3 text-[#0F172A] focus:border-[#0A66C2] focus:ring-1 focus:ring-[#0A66C2] outline-none transition-all placeholder:text-[#94A3B8]',
                'placeholder': 'Detailed overview of the project objectives and roadmap...'
            }),
            'looking_for': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full bg-white border border-[#E2E8F0] rounded-xl px-4 py-3 text-[#0F172A] focus:border-[#0A66C2] focus:ring-1 focus:ring-[#0A66C2] outline-none transition-all placeholder:text-[#94A3B8]',
                'placeholder': 'Specify the expertise, commitment, and background required...'
            }),

            # Using Select dropdowns with Tailwind styling for the new choice fields
            'project_type': forms.Select(attrs={
                'class': 'w-full bg-white border border-[#E2E8F0] rounded-xl px-4 py-3 text-[#0F172A] focus:border-[#0A66C2] focus:ring-1 focus:ring-[#0A66C2] outline-none transition-all cursor-pointer'
            }),
            'project_stage': forms.Select(attrs={
                'class': 'w-full bg-white border border-[#E2E8F0] rounded-xl px-4 py-3 text-[#0F172A] focus:border-[#0A66C2] focus:ring-1 focus:ring-[#0A66C2] outline-none transition-all cursor-pointer'
            }),
            'need_type': forms.Select(attrs={
                'class': 'w-full bg-white border border-[#E2E8F0] rounded-xl px-4 py-3 text-[#0F172A] focus:border-[#0A66C2] focus:ring-1 focus:ring-[#0A66C2] outline-none transition-all cursor-pointer'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)