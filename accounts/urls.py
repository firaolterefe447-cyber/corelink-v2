from django.urls import path
from . import views
from .views import CoreLinkPasswordChangeView
from django.contrib.auth import views as auth_views

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
    # Password Reset (Standard Django Flow)
    path(
        "password/reset/",
        views.CustomPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password/reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="auth/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "password/reset/confirm/<token>/",
        views.CustomPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password/reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="auth/password_reset_complete.html"
        ),
        name="password_reset_complete",
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
