import logging
from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import PasswordChangeForm

# --- MODEL IMPORTS ---
from .models import (
    CustomUser,
    StaffUser,
    UniversalSocialLink,
    UniversalContactMethod,
    ApplicationRequest,
    CommunityContributor,
    Institution,
)

# --- PROFILE IMPORTS (UPDATED FOR UNIFIED ARCHITECTURE) ---
from profiles.models import (
    UserProfile,
    ProfileHeadline,
    Company,
    CompanyMember
)

logger = logging.getLogger(__name__)


# ==============================================================================
# 0. UI MIXINS & UTILITIES
# ==============================================================================


class StaffUserForm(forms.ModelForm):
    # Use a password widget so the characters are hidden while typing
    password = forms.CharField(widget=forms.PasswordInput(), required=False)

    class Meta:
        model = StaffUser
        fields = (
            "full_name",
            "phone_number",
            "password",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data["password"]:
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            self.save_m2m()
        return user


class TailwindFormMixin:
    """
    Supercharged Mixin: Adds Icons, Hover Effects, and Pro Typography.
    Optimized for Tailwind CSS.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # --- ICON ASSETS (Encoded SVGs for CSS) ---
        ICONS = {
            "user": "%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' /%3E%3C/svg%3E",
            "mail": "%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z' /%3E%3C/svg%3E",
            "lock": "%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z' /%3E%3C/svg%3E",
            "calendar": "%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' /%3E%3C/svg%3E",
            "link": "%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1' /%3E%3C/svg%3E",
            "chevron": "%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M19 9l-7 7-7-7' /%3E%3C/svg%3E",
        }

        base_classes = (
            "w-full bg-slate-50 border border-slate-200 rounded-xl "
            "text-sm font-bold text-slate-800 placeholder-slate-400 "
            "focus:bg-white focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10 "
            "outline-none transition-all duration-200 ease-in-out "
            "shadow-sm hover:border-slate-300"
        )

        for field_name, field in self.fields.items():
            widget = field.widget
            extra_classes = " px-4 py-3"

            if isinstance(widget, forms.EmailInput) or "email" in field_name:
                extra_classes = f" pl-11 py-3 bg-[url('data:image/svg+xml,{ICONS['mail']}')] bg-no-repeat bg-[left_1rem_center] bg-[length:1.2rem]"
            elif (
                    isinstance(widget, forms.URLInput)
                    or "url" in field_name
                    or "link" in field_name
                    or "website" in field_name
            ):
                extra_classes = f" pl-11 py-3 bg-[url('data:image/svg+xml,{ICONS['link']}')] bg-no-repeat bg-[left_1rem_center] bg-[length:1.2rem]"
            elif isinstance(widget, forms.DateInput) or "date" in field_name:
                extra_classes = f" pl-11 py-3 bg-[url('data:image/svg+xml,{ICONS['calendar']}')] bg-no-repeat bg-[left_1rem_center] bg-[length:1.2rem]"
            elif isinstance(widget, forms.PasswordInput):
                extra_classes = f" pl-11 py-3 bg-[url('data:image/svg+xml,{ICONS['lock']}')] bg-no-repeat bg-[left_1rem_center] bg-[length:1.2rem]"
            elif isinstance(widget, forms.Select):
                extra_classes = f" px-4 py-3 appearance-none bg-[url('data:image/svg+xml,{ICONS['chevron']}')] bg-no-repeat bg-[right_1rem_center] bg-[length:1.2rem] cursor-pointer"
            elif isinstance(widget, forms.CheckboxInput):
                base_classes = "w-5 h-5 text-emerald-600 bg-slate-100 border-slate-300 rounded focus:ring-emerald-500 focus:ring-offset-0 cursor-pointer"
                extra_classes = ""
            elif isinstance(widget, forms.Textarea):
                extra_classes = " px-4 py-3 h-32 resize-none leading-relaxed"

            existing_classes = widget.attrs.get("class", "")
            widget.attrs["class"] = (
                f"{existing_classes} {base_classes} {extra_classes}".strip()
            )


def normalize_eth_phone(phone: str) -> str:
    """Centralized logic to clean phone numbers. Auto-formats Ethiopian numbers, supports international."""
    if not phone:
        return ""
    phone = phone.replace(" ", "").replace("-", "").strip()

    # Local Ethiopian formats
    if phone.startswith("0") and len(phone) == 10:
        return f"+251{phone[1:]}"
    elif len(phone) == 9 and not phone.startswith("+"):
        return f"+251{phone}"
    elif phone.startswith("251") and len(phone) == 12:
        return f"+{phone}"

    # If it already starts with '+', it's an international number, leave it alone
    if phone.startswith("+"):
        return phone

    # If a user entered an international number without a '+', append it
    if phone.isdigit() and len(phone) >= 10:
        return f"+{phone}"

    return phone


# ==============================================================================
# 1. AUTHENTICATION FORMS
# ==============================================================================


class UserLoginForm(TailwindFormMixin, forms.Form):
    login_identifier = forms.CharField(
        label=_("Phone Number or Email"),
        widget=forms.TextInput(
            attrs={
                "placeholder": "e.g. 09..., +86... or email@example.com",
                "autofocus": "true",
            }
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••"}),
    )

    def clean_login_identifier(self):
        identifier = self.cleaned_data.get("login_identifier", "").strip()
        if "@" in identifier:
            # Assume email
            return identifier
        else:
            # Assume phone
            phone = normalize_eth_phone(identifier)

            # Allow international formats during login
            if not (phone.startswith("+") and phone[1:].isdigit() and 7 <= len(phone[1:]) <= 15):
                raise ValidationError(
                    _("Invalid Phone Format. Please use 09..., 07... or include country code (e.g., +86...).")
                )
            return phone


class EmailRegistrationForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["email"]
        widgets = {
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "Enter your primary email address",
                    "required": "true",
                }
            )
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_("This email is already in use by another account."))
        return email


class VerifyOTPForm(TailwindFormMixin, forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "123456", "autocomplete": "one-time-code"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["otp"].label = "Verification Code"


class GoogleRoleSelectionForm(TailwindFormMixin, forms.Form):
    role = forms.ChoiceField(
        choices=[
            (CustomUser.Role.VISIONARY, _("Visionary")),
            (CustomUser.Role.EXPERT, _("Expert")),
            (CustomUser.Role.FOUNDER, _("Founder")),
        ],
        widget=forms.RadioSelect,
        required=True,
        label=_("Choose your role"),
    )


# ==============================================================================
# 2. IDENTITY MANAGEMENT FORMS
# ==============================================================================


class UniversalSocialLinkForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = UniversalSocialLink
        fields = ["platform_name", "url"]
        help_texts = {
            "platform_name": "The name of the platform where you are active.",
            "url": "The web address (link) to your profile so others can connect with you.",
        }
        widgets = {
            "platform_name": forms.TextInput(
                attrs={"placeholder": "e.g. LinkedIn, GitHub, Portfolio"}
            ),
            "url": forms.URLInput(
                attrs={"placeholder": "https://www.linkedin.com/in/yourprofile"}
            ),
        }


class UniversalContactMethodForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = UniversalContactMethod
        fields = ["type", "value"]
        help_texts = {
            "type": "The way people should reach out (e.g., Email, Phone, or Telegram).",
            "value": "Your contact handle or address (e.g., your@email.com).",
        }
        widgets = {
            "type": forms.TextInput(
                attrs={"placeholder": "e.g. Email, Phone, Telegram"}
            ),
            "value": forms.TextInput(
                attrs={"placeholder": "Enter the contact details..."}
            ),
        }


class AvatarUpdateForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["avatar"]
        widgets = {"avatar": forms.FileInput()}


# ==============================================================================
# 3. ONBOARDING APPLICATION FORMS (The Airlock)
# ==============================================================================

import base64
import uuid
from django.core.files.base import ContentFile


class BaseRegistrationForm(TailwindFormMixin, forms.ModelForm):
    # 🟢 WORLD-CLASS UPGRADE: Autocomplete attributes added to help password managers (Card 8)
    first_name = forms.CharField(label=_("First Name"), max_length=150,
                                 widget=forms.TextInput(
                                     attrs={"placeholder": "First Name", "autocomplete": "given-name"}))
    last_name = forms.CharField(label=_("Last Name"), max_length=150,
                                widget=forms.TextInput(
                                    attrs={"placeholder": "Last Name", "autocomplete": "family-name"}))

    # 🟢 WORLD-CLASS UPGRADE: Upgraded "4 digit PIN" to proper secure password fields (Card 3)
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••", "autocomplete": "new-password"}),
        label=_("Password (Min. 8 chars)"))
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••", "autocomplete": "new-password"}),
        label=_("Confirm Password"))

    phone_number = forms.CharField(label=_("Phone Number"),
                                   widget=forms.TextInput(
                                       attrs={"placeholder": "09... or +86...", "autocomplete": "tel"}))
    email = forms.EmailField(label=_("Email Address"),
                             widget=forms.EmailInput(
                                 attrs={"placeholder": "example@domain.com", "autocomplete": "email"}), required=True)
    telegram_handle = forms.CharField(label=_("Telegram Username"), max_length=100, required=False,
                                      widget=forms.TextInput(attrs={"placeholder": "@username"}))

    avatar = forms.ImageField(label=_("Profile Picture"), required=False, widget=forms.FileInput())

    # ✅ Hidden text field to carry the cropped image data safely
    avatar_base64 = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = CustomUser
        fields = ["phone_number", "email"]

    def clean_phone_number(self):
        phone = normalize_eth_phone(self.cleaned_data.get("phone_number", ""))
        if not (phone.startswith("+") and phone[1:].isdigit() and 7 <= len(phone[1:]) <= 15):
            raise ValidationError(_("Invalid Format. Use 09..., 07..., or include your country code (e.g., +86...)."))
        if CustomUser.objects.filter(phone_number=phone).exists():
            raise ValidationError(_("This phone number is already registered. Please login."))
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        # 🟢 WORLD-CLASS UPGRADE: Enforcing secure password parity server-side (Card 3)
        if password and len(password) < 8:
            self.add_error("password", _("Password must be at least 8 characters long for security."))

        if password != confirm_password:
            self.add_error("confirm_password", _("Passwords do not match."))

        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            email = email.lower().strip()
            if CustomUser.objects.filter(email=email).exists():
                raise ValidationError(_("This email is already registered. Please login."))
        return email

    def save_user(self, role_type):
        user = super().save(commit=False)
        user.role = role_type
        user.set_password(self.cleaned_data["password"])

        first_name = (self.cleaned_data.get("first_name") or "").strip()
        last_name = (self.cleaned_data.get("last_name") or "").strip()
        user.first_name = first_name
        user.last_name = last_name
        user.full_name = f"{first_name} {last_name}".strip()
        user.telegram_handle = (self.cleaned_data.get("telegram_handle") or "").strip()

        # ✅ THE MAGIC: Decode the Base64 text string back into a real image file!
        avatar_b64 = self.cleaned_data.get("avatar_base64")
        if avatar_b64 and ";base64," in avatar_b64:
            try:
                format_str, imgstr = avatar_b64.split(';base64,')
                ext = format_str.split('/')[-1]
                # Create a unique filename
                filename = f"avatar_{uuid.uuid4().hex[:8]}.{ext}"
                user.avatar.save(filename, ContentFile(base64.b64decode(imgstr)), save=False)
            except Exception as e:
                logger.error(f"Failed to decode base64 avatar: {e}")
        elif self.cleaned_data.get("avatar"):
            user.avatar = self.cleaned_data["avatar"]

        user.is_verified = role_type in ["EXPERT", "VISIONARY"]
        user.is_active = True
        user.save()
        return user


class UnifiedOnboardingForm(BaseRegistrationForm):
    ROLE_CHOICES = [
        ('EXPERT', 'Professional / Learner'),
        ('FOUNDER', 'Business / Company'),
    ]

    selected_role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.HiddenInput(),
        required=False,
        initial='EXPERT'
    )

    # ---------------------------------------------------------
    # SHARED FIELDS
    # ---------------------------------------------------------
    # 🟢 WORLD-CLASS UPGRADE: Autocomplete for Location (Card 8)
    city_name = forms.CharField(
        label=_("City"),
        required=True,
        widget=forms.TextInput(
            attrs={"placeholder": _("e.g. Addis Ababa or Hawassa"), "autocomplete": "address-level2"}),
        help_text=_("Please type the exact spelling of your city."),
    )

    # ---------------------------------------------------------
    # INDIVIDUAL (EXPERT / VISIONARY) SPECIFIC FIELDS
    # ---------------------------------------------------------
    institution_name = forms.CharField(
        label=_("Institution / Company / Self-Learning"),
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": _("e.g. Addis Ababa University, Ethio Telecom, or Self-Learning")}
        ),
        help_text=_("Enter your institution, company, or write 'Self-Learning'."),
    )

    current_role = forms.CharField(
        label=_("Professional / Academic Identity"),
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": _("e.g. Third Year Computer Science Student or Senior Dev")}
        ),
        help_text=_("Write fully (e.g., Software Developer or Senior Accountant)."),
    )

    bio_narrative = forms.CharField(
        label=_("About Me / Your Goals"),
        required=False,
        widget=forms.Textarea(
            attrs={
                "placeholder": _(
                    "Tell us a bit about your background, what you are building, or what you want to achieve..."),
                "rows": 4,
            }
        ),
        help_text=_("Share your story. This will act as the bio on your public portfolio. Minimum 150 characters."),
        min_length=150,
    )

    cv_file = forms.FileField(
        label=_("Upload CV (PDF)"),
        required=False,
        widget=forms.FileInput(),
        help_text=_("Optional: Upload your CV or Resume (PDF only, max 5MB).")
    )

    # ---------------------------------------------------------
    # FOUNDER / COMPANY SPECIFIC FIELDS
    # ---------------------------------------------------------
    company_name = forms.CharField(
        label=_("Company / Startup Name"),
        required=False,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. CoreLink Technologies")}),
    )
    founder_role = forms.CharField(
        label=_("Your Role in the Company"),
        required=False,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. Founder, CEO, Lead Developer")}),
    )
    sector = forms.CharField(
        label=_("Industry / Sector"),
        required=False,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. Fintech, EdTech, Agriculture")}),
    )

    company_mission = forms.CharField(
        label=_("Company Mission / Overview"),
        required=False,
        widget=forms.Textarea(
            attrs={
                "placeholder": _("What does your company do? What is the core mission or product you are building?"),
                "rows": 4,
            }
        ),
        help_text=_("Share your company's core mission. This will be displayed on the public Company Profile."),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].help_text = _(
            "IMPORTANT: We will send a verification link here. Please use your active, current email address."
        )

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("selected_role") or "EXPERT"

        # 🟢 WORLD-CLASS UPGRADE: Client/Server Validation Parity (Card 15)
        # Bypassing JS in the browser will no longer allow users to submit empty/short required fields.
        if role in ["EXPERT", "VISIONARY"]:
            if not cleaned_data.get("current_role"):
                self.add_error("current_role", _("Please specify your professional/academic identity."))

            inst_name = cleaned_data.get("institution_name")
            if not inst_name:
                self.add_error("institution_name", _("Please specify your institution or enter 'Self-Learning'."))
            else:
                institution, created = Institution.objects.get_or_create(
                    name__iexact=inst_name,
                    defaults={"name": inst_name, "is_verified": False},
                )
                cleaned_data["institution"] = institution

            # Explicit Server-Side Length Enforcement
            bio_text = cleaned_data.get("bio_narrative", "").strip()
            if len(bio_text) < 150:
                self.add_error("bio_narrative", _("Please write at least 150 characters to build a strong profile."))

        elif role == "FOUNDER":
            if not cleaned_data.get("company_name"):
                self.add_error("company_name", _("Company name is required."))
            if not cleaned_data.get("founder_role"):
                self.add_error("founder_role", _("Your role in the company is required."))
            if not cleaned_data.get("sector"):
                self.add_error("sector", _("Please specify your industry sector."))

            # Explicit Server-Side Length Enforcement
            mission_text = cleaned_data.get("company_mission", "").strip()
            if len(mission_text) < 150:
                self.add_error("company_mission", _("Please write at least 150 characters explaining your mission."))

        return cleaned_data

    def save(self, commit=True):
        with transaction.atomic():
            role = self.cleaned_data.get("selected_role") or "EXPERT"

            # 1. SAVE BASE USER
            user = self.save_user(role_type=role)

            if self.cleaned_data.get("phone_number"):
                UniversalContactMethod.objects.create(
                    user=user, type="Phone", value=self.cleaned_data["phone_number"]
                )

            # Extract shared data
            loc_str = self.cleaned_data.get("city_name", "").strip()

            # 🟢 DYNAMICALLY PULL EITHER BIO OR MISSION
            bio_text = self.cleaned_data.get("bio_narrative", "").strip()
            mission_text = self.cleaned_data.get("company_mission", "").strip()

            user.current_location = loc_str
            user.save(update_fields=["current_location"])

            # 2. EVERYONE GETS A UNIVERSAL PROFILE NOW (Founders get an empty bio, filled later if they want)
            profile = UserProfile.objects.create(
                user=user,
                location=loc_str,
                bio_narrative=bio_text if role in ["EXPERT", "VISIONARY"] else "",
                years_experience=0,
            )

            # Handle CV file upload if provided
            cv_file = self.cleaned_data.get("cv_file")
            if cv_file:
                # Validate it's a PDF
                if not cv_file.name.lower().endswith('.pdf'):
                    self.add_error("cv_file", _("CV must be a PDF document."))
                    raise ValidationError(_("CV must be a PDF document."))
                if cv_file.size > 5 * 1024 * 1024:
                    self.add_error("cv_file", _("CV file size must be under 5MB."))
                    raise ValidationError(_("CV file size must be under 5MB."))
                profile.cv_file = cv_file
                profile.save(update_fields=["cv_file"])

            # 3. ROUTE BASED ON ROLE (THE LEGO BLOCK ARCHITECTURE)
            snapshot_data = {
                "full_name": user.full_name,
                "phone_number": str(self.cleaned_data.get("phone_number", "")),
                "location": loc_str,
                "role_type": role
            }

            if role in ["EXPERT", "VISIONARY"]:
                institution = self.cleaned_data.get("institution")
                inst_str = institution.name if institution else ""
                role_str = self.cleaned_data.get("current_role", "").strip()

                profile.institution = inst_str
                profile.save(update_fields=["institution"])

                if role_str:
                    ProfileHeadline.objects.create(profile=profile, title=role_str, is_primary=True, order=0)

                snapshot_data.update({
                    "current_role": role_str,
                    "institution": inst_str,
                    "bio_narrative": bio_text,
                })

            elif role == "FOUNDER":
                company_name = self.cleaned_data.get("company_name", "").strip()
                sector = self.cleaned_data.get("sector", "").strip()
                founder_role = self.cleaned_data.get("founder_role", "").strip()

                # 🟢 Create Independent Company Block with proper mission statement
                company = Company.objects.create(
                    name=company_name,
                    sector=sector,
                    location=loc_str,
                    mission_stmt=mission_text
                )

                CompanyMember.objects.create(
                    company=company,
                    user=user,
                    role="OWNER",
                    job_title=founder_role,
                    is_active=True
                )

                ProfileHeadline.objects.create(profile=profile, title=founder_role, is_primary=True, order=0)

                snapshot_data.update({
                    "company_name": company_name,
                    "sector": sector,
                    "founder_role": founder_role,
                    "company_mission": mission_text
                })

            # 4. FINAL AIRLOCK SNAPSHOT
            ApplicationRequest.objects.create(
                user=user, role_type=role, submission_data=snapshot_data
            )

            return user


# ==============================================================================
# 4. OTHER / ADMIN FORMS
# ==============================================================================


class CommunityContributorForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = CommunityContributor
        fields = [
            "full_name",
            "email",
            "telegram_username",
            "contribution_area",
            "message",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Your Legal Name"}),
            "email": forms.EmailInput(attrs={"placeholder": "example@domain.com"}),
            "telegram_username": forms.TextInput(attrs={"placeholder": "@username"}),
            "contribution_area": forms.TextInput(
                attrs={"placeholder": "e.g. Tech Support, Event Organizing"}
            ),
            "message": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Why do you want to help the hub?"}
            ),
        }


class CustomUserAdminCreationForm(forms.ModelForm):
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••"}),
    )
    confirm_password = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••"}),
    )

    class Meta:
        model = CustomUser
        fields = ("phone_number", "full_name", "role")

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise ValidationError(_("Passwords do not match."))
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class CoreLinkPasswordChangeForm(PasswordChangeForm):
    """Secure password change form with CoreLink Premium UI classes injected."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Automatically apply your premium CSS to all password fields
        for field in self.fields.values():
            field.widget.attrs.update(
                {"class": "premium-input", "placeholder": "••••••••"}
            )


class PasswordResetRequestForm(TailwindFormMixin, forms.Form):
    """Form for requesting password reset via email (standard flow)."""
    email = forms.EmailField(
        label=_("Email Address"),
        widget=forms.EmailInput(
            attrs={
                "placeholder": "example@domain.com",
                "required": "true",
                "autofocus": "true",
            }
        ),
    )


class PasswordResetConfirmForm(TailwindFormMixin, forms.Form):
    """Form for confirming password reset with new password."""
    new_password = forms.CharField(
        label=_("New Password"),
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "••••••••",
                "autocomplete": "new-password",
            }
        ),
        min_length=8,
    )
    confirm_password = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "••••••••",
                "autocomplete": "new-password",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and len(new_password) < 8:
            self.add_error("new_password", _("Password must be at least 8 characters long."))

        if new_password and new_password != confirm_password:
            self.add_error("confirm_password", _("Passwords do not match."))

        return cleaned_data