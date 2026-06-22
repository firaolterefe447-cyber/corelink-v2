from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


class EmailVerificationRequiredMiddleware:
    """Redirect authenticated users to OTP verification until email is verified."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        current_url_name = ""
        if getattr(request, "resolver_match", None):
            current_url_name = request.resolver_match.url_name or ""

        user = getattr(request, "user", None)
        if (
            user
            and user.is_authenticated
            and not user.is_staff
            and not user.email_verified
        ):
            verification_path = reverse("email_verification")
            logout_path = reverse("logout")

            allowed_url_names = {
                "email_verification",
                "register_email",
                "verify_email_token",
                "logout",
                "google_auth_start",
                "google_auth_callback",
                "google_role_selection",
                "create_password",
            }

            if current_url_name in allowed_url_names:
                return self.get_response(request)

            allowed_prefixes = [
                verification_path,
                logout_path,
                "/admin/",
                "/i18n/",
                settings.STATIC_URL,
                settings.MEDIA_URL,
                "/email/verify/",
            ]

            if not any(request.path.startswith(prefix) for prefix in allowed_prefixes):
                return redirect("email_verification")

        return self.get_response(request)
from django.utils.cache import add_never_cache_headers

class DisableClientCachingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Apply no-cache headers to all dynamic HTML or API requests
        if response.has_header('Content-Type') and 'text/html' in response['Content-Type'] or 'application/json' in response['Content-Type']:
            add_never_cache_headers(response)
        return response