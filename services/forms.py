"""
Service Forms - Professional services offered by users
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Service, ServiceGallery


class TailwindFormMixin:
    """Injects Tailwind CSS classes securely."""
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


class ServiceForm(TailwindFormMixin, forms.ModelForm):
    """Form for user services - distinct from company services."""
    class Meta:
        model = Service
        fields = ['title', 'description', 'is_active']

        labels = {
            'title': _("Service Title"),
            'description': _("Service Description"),
            'is_active': _("Currently Available"),
        }

        help_texts = {
            'title': _("The name of the service you offer (e.g., 'Web Development', 'Business Consulting', 'Graphic Design')."),
            'description': _("Provide a detailed explanation of your service, what you deliver, and how you help clients."),
            'is_active': _("Uncheck this if you're not currently accepting new requests for this service."),
        }

        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'e.g., Professional Photography Services'}),
            'description': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Describe your service in detail...', 'class': 'markdown-editor'}),
        }

    def clean_title(self):
        """Ensure title is meaningful."""
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise ValidationError(_("Service title is required."))
        if len(title) < 3:
            raise ValidationError(_("Service title should be at least 3 characters."))
        return title

    def clean_description(self):
        """Ensure meaningful description."""
        desc = self.cleaned_data.get('description', '').strip()
        if not desc:
            raise ValidationError(_("Service description is required. Tell us about your service."))
        if len(desc) < 20:
            raise ValidationError(_("Description should be at least 20 characters. Share more details!"))
        return desc


class ServiceGalleryForm(TailwindFormMixin, forms.ModelForm):
    """Form for adding images to service gallery."""
    class Meta:
        model = ServiceGallery
        fields = ['image', 'caption', 'order']

        labels = {
            'image': _("Upload Image"),
            'caption': _("Image Caption"),
            'order': _("Display Order"),
        }

        help_texts = {
            'image': _("Upload an image showcasing your service work."),
            'caption': _("Optional: Add a brief description for this image."),
            'order': _("Order in which this image appears in the gallery."),
        }

        widgets = {
            'order': forms.NumberInput(attrs={'min': 0, 'placeholder': '0'}),
        }
