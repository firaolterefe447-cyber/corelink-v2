from django.urls import path
from . import views
from .views import CoreLinkPasswordChangeView

urlpatterns = [
    # Authentication
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("verify-email/", views.email_verification_view, name="email_verification"),
    path("auth/google/login/", views.google_auth_start_view, name="google_auth_start"),
    path(
        "auth/google/callback/",
        views.google_auth_callback_view,
        name="google_auth_callback",
    ),
    path(
        "auth/google/role/",
        views.google_role_selection_view,
        name="google_role_selection",
    ),
    path("create-password/", views.create_password_view, name="create_password"),
    # Password Reset (Email Recovery)
    path(
        "password/reset/",
        views.password_reset_method_selection,
        name="password_reset_method_selection",
    ),
    path(
        "password/reset/email/",
        views.password_reset_request_email,
        name="password_reset_request_email",
    ),
    path(
        "password/reset/email/entry/",
        views.password_reset_email_entry,
        name="password_reset_email_entry",
    ),
    path(
        "password/reset/email/verify/",
        views.password_reset_email_verify,
        name="password_reset_email_verify",
    ),
    path(
        "password/reset/confirm/<uidb64>/<token>/",
        views.password_reset_confirm,
        name="password_reset_confirm",
    ),
    # Account Management
    path("privacy/toggle/", views.toggle_privacy, name="toggle_privacy"),
    path("deactivate/", views.deactivate_account, name="deactivate_account"),
    path("email/register/", views.register_email_view, name="register_email"),
    path(
        "email/verify/<str:token>/",
        views.verify_email_token_view,
        name="verify_email_token",
    ),
    path(
        "settings/security/password/",
        CoreLinkPasswordChangeView.as_view(),
        name="password_change",
    ),
    # Unified Onboarding Flow
    path("join/", views.unified_onboarding_view, name="signup"),
    # API Endpoints
    path("api/cities/", views.get_cities, name="api_get_cities"),
]
