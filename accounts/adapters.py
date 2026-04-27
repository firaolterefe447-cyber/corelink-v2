import random

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from django.contrib.auth import login
from django.shortcuts import redirect
from django.urls import reverse

from .models import CustomUser


class CustomAccountAdapter(DefaultAccountAdapter):
    @staticmethod
    def _profile_update_url_name_for_user(user):
        role = (getattr(user, "role", "") or "").upper()
        if role == CustomUser.Role.FOUNDER:
            return "founder_settings"
        if role == CustomUser.Role.EXPERT:
            return "expert_settings"
        return "visionary_settings"

    def get_login_redirect_url(self, request):
        social_onboarding_required = request.session.pop("social_onboarding_required", False)
        if social_onboarding_required:
            return reverse(self._profile_update_url_name_for_user(request.user))
        return reverse("dashboard")


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    @staticmethod
    def _generate_social_phone_number() -> str:
        return f"+999{random.randint(100000000, 999999999)}"

    def _generate_unique_social_phone_number(self) -> str:
        while True:
            candidate = self._generate_social_phone_number()
            if not CustomUser.objects.filter(phone_number=candidate).exists():
                return candidate

    def pre_social_login(self, request, sociallogin):
        if not sociallogin.is_existing:
            email = (sociallogin.user.email or "").strip().lower()
            if not email:
                return

            existing_user = CustomUser.objects.filter(email__iexact=email).first()
            if existing_user:
                existing_social = SocialAccount.objects.filter(
                    provider=sociallogin.account.provider,
                    uid=sociallogin.account.uid,
                ).exists()
                if not existing_social:
                    sociallogin.connect(request, existing_user)
                login(
                    request,
                    existing_user,
                    backend="allauth.account.auth_backends.AuthenticationBackend",
                )

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        email = (user.email or data.get("email") or "").strip().lower()

        given_name = (data.get("given_name") or "").strip()
        family_name = (data.get("family_name") or "").strip()
        provider_full_name = " ".join(part for part in [given_name, family_name] if part).strip()
        display_name = (data.get("name") or "").strip()
        name = (user.full_name or provider_full_name or display_name).strip()

        user.email = email
        user.full_name = name[:150] if name else "CoreLink User"

        if not user.phone_number:
            user.phone_number = self._generate_unique_social_phone_number()

        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)

        if not user.phone_number:
            user.phone_number = self._generate_unique_social_phone_number()

        if user.email:
            user.is_email_verified = True

        user.save(update_fields=["phone_number", "is_email_verified"])

        request.session["social_onboarding_required"] = True
        return user

    def on_authentication_error(self, request, provider, error=None, exception=None, extra_context=None):
        if isinstance(exception, OAuth2Error):
            return redirect(reverse("login"))
        return super().on_authentication_error(request, provider, error, exception, extra_context)