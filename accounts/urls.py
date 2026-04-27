from django.urls import path
from . import views
from .views import CoreLinkPasswordChangeView

urlpatterns = [
    # ==========================================
    # AUTHENTICATION
    # ==========================================
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
    # ==========================================
    # ACCOUNT MANAGEMENT
    # ==========================================
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
    # ==========================================
    # 🚀 NEW UNIFIED ONBOARDING FLOW
    # ==========================================
    path("join/", views.unified_onboarding_view, name="unified_onboarding"),
    path("join/success/", views.application_success_view, name="application_success"),
    # Contributor/Volunteer form wasn't part of the unified form, so it keeps its own view
    path("join/volunteer/", views.apply_contributor_view, name="apply_contributor"),
    # ==========================================
    # API ENDPOINTS
    # ==========================================
    path("api/cities/", views.get_cities, name="api_get_cities"),
]
