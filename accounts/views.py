import logging
import random
import time
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.db import transaction, IntegrityError
from django.db.models.functions import Lower
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core import signing
from django.core.signing import SignatureExpired, BadSignature
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.crypto import constant_time_compare
from django.utils.html import strip_tags
from django.utils.encoding import force_bytes

from django.http import JsonResponse
from .models import City, CustomUser
from .forms import (
    UserLoginForm,
    CommunityContributorForm,
    UnifiedOnboardingForm,
    EmailRegistrationForm,
    VerifyOTPForm,
    GoogleRoleSelectionForm,
    PasswordResetRequestForm,
    PasswordResetConfirmForm,
)

# Setup Logger for Production Debugging
logger = logging.getLogger(__name__)

OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_VERIFY_ATTEMPTS = 5


def _generate_otp_code() -> str:
    return f"{random.randint(100000, 999999)}"


def _mask_email(email: str) -> str:
    if not email or "@" not in email:
        return ""
    local_part, domain = email.split("@", 1)
    if len(local_part) <= 2:
        masked = f"{local_part[0]}*" if local_part else "*"
    else:
        masked = f"{local_part[0]}{'*' * (len(local_part) - 2)}{local_part[-1]}"
    return f"{masked}@{domain}"


def _name_from_email(email: str) -> str:
    local = (email.split("@", 1)[0] if email and "@" in email else "").strip()
    if not local:
        return "CoreLink User"
    normalized = local.replace(".", " ").replace("_", " ").replace("-", " ")
    return " ".join(part.capitalize() for part in normalized.split()) or "CoreLink User"


def _build_verification_token(user: CustomUser, otp_code: str) -> str:
    payload = {
        "uid": str(user.id),
        "email": (user.email or "").lower(),
        "otp": otp_code,
    }
    return signing.dumps(payload, salt="accounts.email-verification")


def _send_verification_otp(user: CustomUser, request=None) -> bool:
    if not user.email:
        return False

    otp_code = _generate_otp_code()
    user.email_otp_code = otp_code
    user.email_otp_expires_at = timezone.now() + timedelta(minutes=10)
    user.save(update_fields=["email_otp_code", "email_otp_expires_at", "updated_at"])

    verify_link = ""
    if request is not None:
        token = _build_verification_token(user, otp_code)
        verify_link = request.build_absolute_uri(f"/verify-email/?token={token}")

    context = {
        "full_name": user.full_name or "there",
        "otp_code": otp_code,
        "expiry_minutes": 10,
        "support_email": settings.DEFAULT_FROM_EMAIL,
        "verify_link": verify_link,
    }
    html_content = render_to_string("emails/email_verification_otp.html", context)
    text_content = strip_tags(html_content)

    email_message = EmailMultiAlternatives(
        subject="CoreLink Email Verification Code",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email_message.attach_alternative(html_content, "text/html")
    email_message.send(fail_silently=False)
    return True


def _get_google_redirect_uri(request) -> str:
    explicit_redirect = getattr(settings, "GOOGLE_OAUTH_REDIRECT_URI", "")
    if explicit_redirect:
        return explicit_redirect
    return request.build_absolute_uri("/auth/google/callback/")


def _generate_google_placeholder_phone() -> str:
    for _ in range(20):
        candidate = f"+2519{random.randint(10_000_000, 99_999_999)}"
        if not CustomUser.objects.filter(phone_number=candidate).exists():
            return candidate
    raise ValueError("Unable to allocate phone number for Google user")


def _send_post_verification_welcome_email(user):
    try:
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        
        display_name = user.full_name or "there"
        html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                    <h2 style="color: #0A66C2;">Welcome to CoreLink, {display_name}!</h2>
                    <p>Your email has been successfully verified.</p>
                    <p>You can now explore opportunities, build your profile, and connect with the community.</p>
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="font-size: 12px; color: #999;">Thanks for joining CoreLink.</p>
                </div>
            </body>
            </html>
        """
        
        text_content = strip_tags(html_content)
        email_message = EmailMultiAlternatives(
            subject="Welcome to CoreLink",
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email_message.attach_alternative(html_content, "text/html")
        email_message.send(fail_silently=False)
    except Exception as exc:
        logger.warning(
            f"Welcome email delivery failed for user_id={user.pk}: {exc}"
        )


# ==============================================================================
# ROUTING HELPER
# ==============================================================================

def _route_user_to_dashboard(user):
    """
    Intelligent routing logic: 
    Founders are sent straight to their Company Admin Dashboard upon login/registration.
    Everyone else goes to the Unified Personal Dashboard.
    """
    if user.role == "FOUNDER":
        # Check if the Founder has an active company attached
        membership = user.company_memberships.filter(
            is_active=True, role__in=['OWNER', 'ADMIN']
        ).select_related('company').first()

        if membership and membership.company:
            return redirect('company_admin_dashboard', slug=membership.company.slug)
        else:
            # Failsafe: If they are a founder but missing a company, send them to create it
            return redirect('company_create')

    # Default fallback for Visionaries and Experts
    return redirect('dashboard')


# ==============================================================================
# ONBOARDING CONTROLLERS (The Application Flow)
# ==============================================================================


def application_success_view(request):
    """
    The 'Waiting Room' page.
    Users (like Founders) are redirected here after submitting their application.
    """
    return render(request, "auth/application_success.html")


# ==============================================================================
# 🚀 NEW UNIFIED ONBOARDING VIEW
# ==============================================================================


def unified_onboarding_view(request):
    """
    Unified Onboarding flow: handles selection of role and subsequent form submission
    for Visionary, Expert, and Founder all in one place.
    """
    if request.user.is_authenticated:
        return _route_user_to_dashboard(request.user)

    if request.method == "POST":
        # request.FILES is required because Expert needs a CV upload
        form = UnifiedOnboardingForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Form save handles atomic creation of User, Profile, Company, Snapshot, etc.
                    user = form.save()
                    role = form.cleaned_data.get("selected_role")

                # Log in the user immediately
                login(
                    request, user, backend="django.contrib.auth.backends.ModelBackend"
                )
                messages.success(
                    request, "Welcome! Your account has been created successfully."
                )
                return _route_user_to_dashboard(user)

            except Exception as e:
                logger.error(f"Unified Onboarding Critical Failure: {str(e)}")
                messages.error(request, "An internal error occurred. Please try again.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UnifiedOnboardingForm()

    # We will render the single unified template here
    return render(request, "auth/unified_onboarding.html", {"form": form})


def apply_contributor_view(request):
    """
    Handles Volunteer/Contributor Registration.
    """
    if request.method == "POST":
        form = CommunityContributorForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Thank you! We will contact you on Telegram.")
                return redirect("application_success")
            except Exception as e:
                logger.error(f"Contributor Application Failed: {str(e)}")
                messages.error(request, "An internal error occurred.")
        else:
            messages.error(request, "Please check your input.")
    else:
        form = CommunityContributorForm()

    return render(request, "auth/apply_contributor.html", {"form": form})


# ==============================================================================
# API ENDPOINTS
# ==============================================================================


@require_http_methods(["GET"])
def get_cities(request):
    country_id = request.GET.get("country_id")
    if country_id:
        try:
            cities = City.objects.filter(
                Country_id=country_id, is_verified=True
            ).order_by(Lower("name"), "name")
            city_list = [{"id": c.id, "name": c.name} for c in cities]
            return JsonResponse({"cities": city_list})
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Invalid country_id in get_cities: {country_id} | Error: {e}"
            )
            return JsonResponse(
                {"cities": [], "error": "Invalid country identifier"}, status=400
            )
        except Exception as e:
            logger.exception(f"Unexpected error in get_cities: {e}")
            return JsonResponse(
                {"cities": [], "error": "Internal server error"}, status=500
            )
    return JsonResponse({"cities": []})


# ==============================================================================
# AUTHENTICATION CONTROLLERS
# ==============================================================================


@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    Handles phone or email based authentication.
    """
    if request.user.is_authenticated:
        return _route_user_to_dashboard(request.user)

    if request.method == "POST":
        form = UserLoginForm(request.POST)
        if form.is_valid():
            login_identifier = form.cleaned_data.get("login_identifier")
            password = form.cleaned_data.get("password")

            auth_username = login_identifier
            if "@" in login_identifier:
                matched_user = CustomUser.objects.filter(
                    email__iexact=login_identifier
                ).first()
                if matched_user:
                    auth_username = matched_user.phone_number

            user = authenticate(request, username=auth_username, password=password)

            if user is not None:
                login(
                    request, user, backend="django.contrib.auth.backends.ModelBackend"
                )

                if not user.email:
                    request.session["pending_verify_user_id"] = str(user.id)
                    messages.warning(
                        request, "Please add and verify your email to continue."
                    )
                    return redirect("email_verification")

                if not user.email_verified:
                    request.session["pending_verify_user_id"] = str(user.id)
                    messages.warning(request, "Please verify your email to continue.")
                    return redirect("email_verification")

                messages.info(
                    request, f"Welcome back, {user.display_name or login_identifier}."
                )

                next_url = request.POST.get("next") or request.GET.get("next")
                if next_url and url_has_allowed_host_and_scheme(
                        url=next_url, allowed_hosts={request.get_host()}
                ):
                    return redirect(next_url)

                return _route_user_to_dashboard(user)
            else:
                messages.error(request, "Invalid phone number/email or password.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserLoginForm()

    return render(request, "auth/login.html", {"login_form": form})


@login_required
def register_email_view(request):
    """
    Prompt user to register or verify their email using OTP.
    """
    if request.user.is_email_verified and request.user.email:
        messages.info(request, "Your email is already verified.")
        return _route_user_to_dashboard(request.user)

    email_sent = request.session.get("verification_email_sent", False)
    pending_email = request.session.get("pending_email")

    # If verification_email_sent is True but no pending_email, reset the state
    if email_sent and not pending_email:
        email_sent = False
        request.session["verification_email_sent"] = False

    if request.method == "POST":
        if "send_otp" in request.POST or "resend" in request.POST:
            last_sent_at = request.session.get("verification_last_sent_at")
            if last_sent_at:
                elapsed = int(time.time() - last_sent_at)
                remaining = OTP_RESEND_COOLDOWN_SECONDS - elapsed
                if remaining > 0:
                    messages.error(
                        request,
                        f"Please wait {remaining} seconds before requesting another code.",
                    )
                    return redirect("register_email")

            # Clear previous messages to avoid duplication if it's a resend or fresh attempt
            storage = messages.get_messages(request)
            storage.used = True

            form = EmailRegistrationForm(request.POST, instance=request.user)
            if form.is_valid():
                # DO NOT save the email to the user model yet
                pending_email = form.cleaned_data.get("email")
                # Use the existing Django SMTP email verification function
                success = _send_verification_otp(request.user, request=request)
                if success:
                    request.session["verification_email_sent"] = True
                    request.session["pending_email"] = pending_email
                    request.session["verification_last_sent_at"] = int(time.time())
                    request.session["otp_verify_attempts"] = 0
                    messages.success(
                        request,
                        f"A 6-digit verification code has been sent to {pending_email}.",
                    )
                    return redirect("register_email")
                else:
                    messages.error(
                        request,
                        "Failed to send verification code. Please try again later.",
                    )

        elif "verify_otp" in request.POST:
            attempts = request.session.get("otp_verify_attempts", 0)
            if attempts >= OTP_MAX_VERIFY_ATTEMPTS:
                messages.error(
                    request,
                    "Too many invalid attempts. Please request a new verification code.",
                )
                return redirect("register_email")

            otp_form = VerifyOTPForm(request.POST)
            if otp_form.is_valid():
                otp = otp_form.cleaned_data.get("otp")
                if not otp:
                    messages.error(request, "Please enter the verification code.")
                else:
                    # Use the existing Django SMTP OTP verification logic
                    now = timezone.now()
                    if (request.user.email_otp_code 
                        and request.user.email_otp_expires_at 
                        and request.user.email_otp_expires_at >= now
                        and constant_time_compare(otp, request.user.email_otp_code)):
                        user = request.user
                        # pending_email is already retrieved above

                        try:
                            if pending_email:
                                user.email = pending_email

                            user.is_email_verified = True
                            user.email_otp_code = None
                            user.email_otp_expires_at = None
                            user.save()
                        except IntegrityError:
                            messages.error(
                                request,
                                "This email is already in use by another account.",
                            )
                            return redirect("register_email")
                        
                        # Cleanup session on successful verification
                        if "verification_email_sent" in request.session:
                            del request.session["verification_email_sent"]
                        if "pending_email" in request.session:
                            del request.session["pending_email"]
                        if "verification_last_sent_at" in request.session:
                            del request.session["verification_last_sent_at"]
                        if "otp_verify_attempts" in request.session:
                            del request.session["otp_verify_attempts"]

                        _send_post_verification_welcome_email(user)

                        messages.success(
                            request, "Your email has been successfully verified!"
                        )

                        # Check if user was coming from password reset flow
                        if request.session.get("pending_password_reset_user_id"):
                            del request.session["pending_password_reset_user_id"]
                            # Clear any password reset session flags
                            if "pending_password_reset_early_user" in request.session:
                                del request.session["pending_password_reset_early_user"]
                            if "pending_password_reset_needs_verification" in request.session:
                                del request.session["pending_password_reset_needs_verification"]
                            
                            return render(request, "auth/email_verified_password_reset.html")

                        # Handle Founders: they might still be unverified by admin
                        if user.role == "FOUNDER" and not user.is_verified:
                            return redirect("application_success")

                        return _route_user_to_dashboard(user)
                    else:
                        request.session["otp_verify_attempts"] = attempts + 1
                        messages.error(request, "Invalid or expired verification code.")
            else:
                messages.error(request, "Please enter a valid 6-digit code.")

    # Prepare forms
    initial_email = pending_email if pending_email else request.user.email
    form = EmailRegistrationForm(
        instance=request.user, initial={"email": initial_email}
    )
    otp_form = VerifyOTPForm()

    return render(
        request,
        "auth/accounts/register_email.html",
        {
            "form": form,
            "otp_form": otp_form,
            "email_sent": email_sent,
            "email_unverified": True,
        },
    )


def verify_email_token_view(request, token):
    try:
        payload = signing.loads(token, salt="accounts.email-verification", max_age=600)  # 10 minutes
        token_email = payload.get("email")
        token_code = payload.get("otp")
        token_uid = payload.get("uid")

        # Find the user
        token_user = CustomUser.objects.filter(pk=token_uid).first()
        if not token_user:
            messages.error(request, "Invalid verification link.")
            return redirect("login")

        # Verify the token matches
        if (
            token_user
            and token_user.email
            and token_email == token_user.email.lower()
            and token_user.email_otp_code
            and token_user.email_otp_expires_at
            and token_user.email_otp_expires_at >= timezone.now()
            and constant_time_compare(token_code, token_user.email_otp_code)
        ):
            token_user.email_verified = True
            token_user.email_otp_code = None
            token_user.email_otp_expires_at = None
            token_user.save(
                update_fields=[
                    "email_verified",
                    "email_otp_code",
                    "email_otp_expires_at",
                    "updated_at",
                ]
            )

            # If user is logged in, redirect to dashboard
            if request.user.is_authenticated:
                if str(request.user.pk) != token_uid:
                    messages.error(
                        request, "This verification link does not belong to your account."
                    )
                    return redirect("register_email")
                
                # Cleanup session if this matches the pending email
                if request.session.get("pending_email") == token_email:
                    if "verification_email_sent" in request.session:
                        del request.session["verification_email_sent"]
                    if "pending_email" in request.session:
                        del request.session["pending_email"]
                    if "verification_last_sent_at" in request.session:
                        del request.session["verification_last_sent_at"]
                    if "otp_verify_attempts" in request.session:
                        del request.session["otp_verify_attempts"]

                messages.success(request, "Email verified successfully!")
                
                # Check if user was coming from password reset flow
                if request.session.get("pending_password_reset_user_id"):
                    del request.session["pending_password_reset_user_id"]
                    # Clear any password reset session flags
                    if "pending_password_reset_early_user" in request.session:
                        del request.session["pending_password_reset_early_user"]
                    if "pending_password_reset_needs_verification" in request.session:
                        del request.session["pending_password_reset_needs_verification"]
                    
                    return render(request, "auth/email_verified_password_reset.html")
                
                return redirect("dashboard")
            else:
                # User not logged in, redirect to login
                messages.success(request, "Email verified successfully! Please login.")
                return redirect("login")
        else:
            messages.error(request, "Invalid or expired verification link.")
            return redirect("login")
    except (SignatureExpired, BadSignature):
        messages.error(request, "Invalid or expired verification link.")
        return redirect("login")


@require_http_methods(["GET", "POST"])
def email_verification_view(request):
    token = (request.GET.get("token") or "").strip()
    if request.method == "GET" and token:
        try:
            payload = signing.loads(
                token, salt="accounts.email-verification", max_age=600
            )
            token_user = CustomUser.objects.filter(pk=payload.get("uid")).first()
            token_code = (payload.get("otp") or "").strip()
            token_email = (payload.get("email") or "").strip().lower()

            if not token_user:
                messages.error(request, "Invalid verification link. User not found.")
                return redirect("login")

            # If already verified, don't force OTP form again.
            if (
                    token_user.email_verified
                    and token_user.email
                    and token_email == token_user.email.lower()
            ):
                login(
                    request,
                    token_user,
                    backend="django.contrib.auth.backends.ModelBackend",
                )
                request.session.pop("pending_verify_user_id", None)
                messages.success(request, "Your email is already verified.")
                return _route_user_to_dashboard(token_user)

            if (
                    token_user
                    and token_user.email
                    and token_email == token_user.email.lower()
                    and token_user.email_otp_code
                    and token_user.email_otp_expires_at
                    and token_user.email_otp_expires_at >= timezone.now()
                    and constant_time_compare(token_code, token_user.email_otp_code)
            ):
                token_user.email_verified = True
                token_user.email_otp_code = None
                token_user.email_otp_expires_at = None
                token_user.save(
                    update_fields=[
                        "email_verified",
                        "email_otp_code",
                        "email_otp_expires_at",
                        "updated_at",
                    ]
                )
                login(
                    request,
                    token_user,
                    backend="django.contrib.auth.backends.ModelBackend",
                )
                request.session.pop("pending_verify_user_id", None)
                messages.success(request, "Email verified successfully.")
                return _route_user_to_dashboard(token_user)
            messages.error(request, "Verification link is invalid or has expired.")
            return redirect("login")
        except signing.SignatureExpired:
            messages.error(
                request, "Verification link expired. Request a new OTP code."
            )
            return redirect("login")
        except signing.BadSignature:
            messages.error(
                request, "Invalid verification link. Request a new OTP code."
            )
            return redirect("login")

    pending_user_id = request.session.get("pending_verify_user_id")

    user = request.user if request.user.is_authenticated else None
    if not user and pending_user_id:
        user = CustomUser.objects.filter(pk=pending_user_id).first()

    if not user:
        messages.error(request, "Please log in to verify your email.")
        return redirect("login")

    if user.email_verified and user.email:
        request.session.pop("pending_verify_user_id", None)
        messages.success(request, "Your email is already verified.")
        return _route_user_to_dashboard(user)

    if request.method == "POST":
        action = request.POST.get("action")
        email = (request.POST.get("email") or user.email or "").strip().lower()

        if action == "send_otp":
            if not email:
                messages.error(request, "Please enter a valid email.")
            elif (
                    CustomUser.objects.filter(email__iexact=email)
                            .exclude(pk=user.pk)
                            .exists()
            ):
                messages.error(
                    request, "That email is already used by another account."
                )
            else:
                user.email = email
                user.email_verified = False
                user.save(update_fields=["email", "email_verified", "updated_at"])
                try:
                    _send_verification_otp(user, request=request)
                    messages.success(request, "Verification code sent to your email.")
                except Exception as exc:
                    logger.error(f"Email OTP send failed for user {user.pk}: {exc}")
                    messages.error(
                        request, "Unable to send email right now. Please try again."
                    )

        if action == "verify_otp":
            raw_code = request.POST.get("otp") or ""
            otp_code = "".join(ch for ch in raw_code if ch.isdigit())
            now = timezone.now()

            if not otp_code:
                messages.error(request, "Please enter the OTP code.")
            elif not user.email_otp_code or not user.email_otp_expires_at:
                messages.error(request, "Request a new OTP code first.")
            elif user.email_otp_expires_at < now:
                messages.error(
                    request, "Your OTP code has expired. Please request a new one."
                )
            elif not constant_time_compare(otp_code, user.email_otp_code):
                messages.error(request, "Invalid OTP code. Please try again.")
            else:
                user.email_verified = True
                user.email_otp_code = None
                user.email_otp_expires_at = None
                user.save(
                    update_fields=[
                        "email_verified",
                        "email_otp_code",
                        "email_otp_expires_at",
                        "updated_at",
                    ]
                )

                if not request.user.is_authenticated:
                    login(
                        request,
                        user,
                        backend="django.contrib.auth.backends.ModelBackend",
                    )

                request.session.pop("pending_verify_user_id", None)
                messages.success(request, "Email verified successfully.")
                return _route_user_to_dashboard(user)

    return render(
        request,
        "auth/email_verification.html",
        {
            "verification_email": user.email or "",
            "masked_email": _mask_email(user.email or ""),
            "otp_expired": bool(
                user.email_otp_expires_at and user.email_otp_expires_at < timezone.now()
            ),
        },
    )


def google_auth_start_view(request):
    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    if not client_id:
        messages.error(request, "Google sign-in is not configured yet.")
        return redirect("login")

    redirect_uri = _get_google_redirect_uri(request)
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
            "include_granted_scopes": "true",
            "prompt": "select_account",
        }
    )
    return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{query}")


def google_auth_callback_view(request):
    if request.GET.get("error"):
        messages.error(request, "Google sign-in was cancelled.")
        return redirect("login")

    code = request.GET.get("code")
    if not code:
        messages.error(request, "Google sign-in failed. Missing authorization code.")
        return redirect("login")

    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
    redirect_uri = _get_google_redirect_uri(request)

    if not client_id or not client_secret:
        messages.error(request, "Google sign-in is not configured yet.")
        return redirect("login")

    try:
        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_response.raise_for_status()
        token_data = token_response.json()

        access_token = token_data.get("access_token")
        if not access_token:
            messages.error(
                request, "Google sign-in failed while requesting access token."
            )
            return redirect("login")

        userinfo_response = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        userinfo_response.raise_for_status()
        google_user = userinfo_response.json()
    except requests.RequestException as exc:
        logger.error(f"Google OAuth exchange failed: {exc}")
        messages.error(
            request, "Google sign-in is temporarily unavailable. Please try again."
        )
        return redirect("login")

    email = (google_user.get("email") or "").strip().lower()
    sub = google_user.get("sub")
    google_name = (google_user.get("name") or "").strip()
    is_google_email_verified = bool(google_user.get("email_verified"))

    if not email or not sub:
        messages.error(request, "Google did not return enough profile information.")
        return redirect("login")

    existing_user = CustomUser.objects.filter(email__iexact=email).first()
    if existing_user:
        if existing_user.google_sub and existing_user.google_sub != sub:
            messages.error(
                request, "This email is linked to a different Google account."
            )
            return redirect("login")

        fields_to_update = []
        if not existing_user.google_sub:
            existing_user.google_sub = sub
            fields_to_update.append("google_sub")
        if is_google_email_verified and not existing_user.email_verified:
            existing_user.email_verified = True
            fields_to_update.append("email_verified")
        if google_name and not existing_user.full_name:
            existing_user.full_name = google_name
            fields_to_update.append("full_name")

        if fields_to_update:
            fields_to_update.append("updated_at")
            existing_user.save(update_fields=fields_to_update)

        login(
            request,
            existing_user,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        if not existing_user.email_verified:
            request.session["pending_verify_user_id"] = str(existing_user.id)
            return redirect("email_verification")

        return _route_user_to_dashboard(existing_user)

    try:
        created_user = CustomUser.objects.create(
            phone_number=_generate_google_placeholder_phone(),
            full_name=google_name or _name_from_email(email),
            role=CustomUser.Role.VISIONARY,
            email=email,
            email_verified=is_google_email_verified,
            google_sub=sub,
            is_verified=True,
            is_active=True,
        )
        created_user.set_unusable_password()
        created_user.save(update_fields=["password", "updated_at"])
    except Exception as exc:
        logger.exception(f"Google user auto-registration failed: {exc}")
        messages.error(request, "Unable to complete Google sign-in. Please try again.")
        return redirect("login")

    login(
        request,
        created_user,
        backend="django.contrib.auth.backends.ModelBackend",
    )
    request.session["needs_role_selection"] = True
    messages.success(
        request, "Account created with Google. Choose your role to continue."
    )
    return redirect("google_role_selection")


@login_required
@require_http_methods(["GET", "POST"])
def google_role_selection_view(request):
    if not request.user.google_sub:
        return _route_user_to_dashboard(request.user)

    if request.method == "POST":
        form = GoogleRoleSelectionForm(request.POST)
        if form.is_valid():
            selected_role = form.cleaned_data["role"]
            request.user.role = selected_role
            request.user.is_verified = True
            request.user.save(update_fields=["role", "is_verified", "updated_at"])

            if not request.user.has_usable_password():
                messages.info(
                    request,
                    "Now create a password so you can also sign in with phone/email.",
                )
                return redirect("create_password")

            request.session.pop("needs_role_selection", None)
            messages.success(request, "Role updated successfully.")
            return _route_user_to_dashboard(request.user)
    else:
        form = GoogleRoleSelectionForm(initial={"role": request.user.role})

    return render(request, "auth/google_role_selection.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def create_password_view(request):
    if request.method == "POST":
        form = SetPasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            request.session.pop("needs_role_selection", None)
            messages.success(request, "Password created successfully.")
            return _route_user_to_dashboard(request.user)
    else:
        form = SetPasswordForm(request.user)

    return render(request, "auth/create_password.html", {"form": form})


def logout_view(request):
    """
    Terminates session and redirects to home.
    """
    logout(request)
    messages.info(request, "You have been securely logged out.")
    return redirect("home")


# ==============================================================================
# PRIVACY & ACCOUNT MANAGEMENT
# ==============================================================================


@login_required
@require_POST
def toggle_privacy(request):
    """
    Panic Button / Stealth Mode:
    Toggles the user's is_public field.
    """
    user = request.user
    user.is_public = not user.is_public
    user.save()

    if user.is_public:
        messages.success(
            request, "Privacy Updated: You are now VISIBLE to the network."
        )
    else:
        messages.warning(request, "Privacy Updated: You are now HIDDEN (Stealth Mode).")

    return redirect(request.META.get("HTTP_REFERER", "/"))


@login_required
def deactivate_account(request):
    """
    Soft Delete / Account Departure:
    Sets is_active=False so they vanish without us losing database integrity.
    """
    if request.method == "POST":
        user = request.user
        user.is_active = False
        user.save()
        logout(request)
        messages.info(
            request,
            "Your account has been deactivated and removed from the public platform.",
        )
        return redirect("login")

    return render(request, "accounts/deactivate_confirm.html")


from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse_lazy
from .forms import (
    CoreLinkPasswordChangeForm,
)  # Adjust import if you put the form somewhere else


class CoreLinkPasswordChangeView(PasswordChangeView):
    """Handles secure password updating and bounces back to Settings."""

    form_class = CoreLinkPasswordChangeForm
    template_name = "dashboard/portfolio/password_change.html"
    success_url = reverse_lazy("profile_settings")  # Redirect back to settings!

    def form_valid(self, form):
        # Add a beautiful success message when they finish
        messages.success(
            self.request, "Success! Your password has been securely updated."
        )


# ==============================================================================
# PASSWORD RESET VIEWS (EMAIL RECOVERY)
# ==============================================================================


def _send_password_reset_email(user, request) -> bool:
    """Send password reset email with secure token."""
    if not user.email:
        return False

    # Generate secure token using Django's default token generator
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Build reset link
    reset_link = request.build_absolute_uri(
        f"/password/reset/confirm/{uid}/{token}/"
    )

    context = {
        "full_name": user.full_name or "there",
        "reset_link": reset_link,
        "expiry_hours": 24,  # Token validity period
        "support_email": settings.DEFAULT_FROM_EMAIL,
    }
    
    html_content = render_to_string("emails/password_reset.html", context)
    text_content = strip_tags(html_content)

    email_message = EmailMultiAlternatives(
        subject="CoreLink Password Reset Request",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email_message.attach_alternative(html_content, "text/html")
    
    try:
        email_message.send(fail_silently=False)
        return True
    except Exception as exc:
        logger.error(f"Password reset email failed for user {user.pk}: {exc}")
        return False


def password_reset_method_selection(request):
    """
    Landing page for password recovery - user chooses Email or Telegram.
    """
    return render(request, "auth/password_reset_method_selection.html")


def password_reset_request_email(request):
    """
    Handle password reset request via phone number.
    Checks user by phone number, then handles email verification status.
    """
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data["phone_number"].strip()
            
            # Find user by phone number
            user = CustomUser.objects.filter(phone_number=phone_number).first()
            
            if not user:
                # Don't reveal if phone number exists or not for security
                messages.info(
                    request,
                    "If an account with this phone number exists, a password reset link has been sent to your email."
                )
                return render(request, "auth/password_reset_email_sent.html")
            
            # Check if user has email at all
            if not user.email:
                # User doesn't have email entered - early launch user
                request.session["pending_password_reset_user_id"] = str(user.id)
                request.session["pending_password_reset_early_user"] = True
                return redirect("password_reset_email_entry")
            
            # Check if user has verified email
            if not user.is_email_verified:
                # User has email but not verified - ask them to verify first
                request.session["pending_password_reset_user_id"] = str(user.id)
                request.session["pending_password_reset_needs_verification"] = True
                request.session["pending_password_reset_email"] = user.email
                return redirect("password_reset_email_verify")
            
            # User has verified email - send reset link
            if _send_password_reset_email(user, request):
                return render(request, "auth/password_reset_email_sent.html")
            else:
                messages.error(
                    request,
                    "Failed to send password reset email. Please try again later."
                )
    else:
        form = PasswordResetRequestForm()
    
    return render(request, "auth/password_reset_request.html", {"form": form})


def password_reset_email_entry(request):
    """
    Allow users to add their email for password reset (for early users without email).
    This works without requiring login.
    """
    user_id = request.session.get("pending_password_reset_user_id")
    if not user_id:
        return redirect("password_reset_request_email")
    
    user = CustomUser.objects.filter(id=user_id).first()
    if not user:
        return redirect("password_reset_request_email")
    
    if request.method == "POST":
        email = request.POST.get("email", "").lower().strip()
        if email:
            # Check if email is already taken by another user
            existing_user = CustomUser.objects.filter(email__iexact=email).exclude(id=user_id).first()
            if existing_user:
                messages.error(request, "This email is already associated with another account.")
            else:
                # Update user's email
                user.email = email
                user.save()
                # Send verification OTP
                if _send_verification_otp(user, request):
                    request.session["verification_email_sent"] = True
                    request.session["pending_email"] = email
                    request.session["verification_last_sent_at"] = int(time.time())
                    request.session["otp_verify_attempts"] = 0
                    request.session["pending_password_reset_needs_verification"] = True
                    request.session["pending_password_reset_email"] = email
                    return redirect("password_reset_email_verify")
                else:
                    messages.error(request, "Failed to send verification code. Please try again later.")
    
    return render(request, "auth/password_reset_email_entry.html")


def password_reset_email_verify(request):
    """
    Allow users to verify their email for password reset.
    This works without requiring login.
    """
    user_id = request.session.get("pending_password_reset_user_id")
    if not user_id:
        return redirect("password_reset_request_email")
    
    user = CustomUser.objects.filter(id=user_id).first()
    if not user:
        return redirect("password_reset_request_email")
    
    email_sent = request.session.get("verification_email_sent", False)
    pending_email = request.session.get("pending_password_reset_email") or request.session.get("pending_email")
    
    if request.method == "POST":
        if "send_otp" in request.POST or "resend" in request.POST:
            last_sent_at = request.session.get("verification_last_sent_at")
            if last_sent_at:
                elapsed = int(time.time()) - last_sent_at
                if elapsed < OTP_COOLDOWN_SECONDS:
                    messages.error(
                        request,
                        f"Please wait {OTP_COOLDOWN_SECONDS - elapsed} seconds before requesting another code.",
                    )
                    return redirect("password_reset_email_verify")
            
            # Send verification OTP
            if _send_verification_otp(user, request):
                request.session["verification_email_sent"] = True
                request.session["pending_email"] = user.email
                request.session["verification_last_sent_at"] = int(time.time())
                request.session["otp_verify_attempts"] = 0
                messages.success(request, f"A 6-digit verification code has been sent to {user.email}.")
            else:
                messages.error(request, "Failed to send verification code. Please try again later.")
        
        elif "verify_otp" in request.POST:
            attempts = request.session.get("otp_verify_attempts", 0)
            if attempts >= OTP_MAX_VERIFY_ATTEMPTS:
                messages.error(
                    request,
                    "Too many invalid attempts. Please request a new verification code.",
                )
                return redirect("password_reset_email_verify")
            
            otp = request.POST.get("otp", "").strip()
            if not otp:
                messages.error(request, "Please enter the verification code.")
            else:
                now = timezone.now()
                if (user.email_otp_code 
                    and user.email_otp_expires_at 
                    and user.email_otp_expires_at >= now
                    and constant_time_compare(otp, user.email_otp_code)):
                    # OTP is valid - verify email
                    user.is_email_verified = True
                    user.email_otp_code = None
                    user.email_otp_expires_at = None
                    user.save()
                    
                    # Clear session
                    if "pending_password_reset_user_id" in request.session:
                        del request.session["pending_password_reset_user_id"]
                    if "pending_password_reset_early_user" in request.session:
                        del request.session["pending_password_reset_early_user"]
                    if "pending_password_reset_needs_verification" in request.session:
                        del request.session["pending_password_reset_needs_verification"]
                    if "pending_password_reset_email" in request.session:
                        del request.session["pending_password_reset_email"]
                    if "verification_email_sent" in request.session:
                        del request.session["verification_email_sent"]
                    if "pending_email" in request.session:
                        del request.session["pending_email"]
                    if "verification_last_sent_at" in request.session:
                        del request.session["verification_last_sent_at"]
                    if "otp_verify_attempts" in request.session:
                        del request.session["otp_verify_attempts"]
                    
                    return render(request, "auth/email_verified_password_reset.html")
                else:
                    request.session["otp_verify_attempts"] = attempts + 1
                    messages.error(request, "Invalid or expired verification code.")
    
    return render(request, "auth/password_reset_email_verify.html", {"email": pending_email, "email_sent": email_sent})


def password_reset_confirm(request, uidb64, token):
    """
    Handle password reset confirmation with token validation.
    """
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, UnicodeDecodeError, CustomUser.DoesNotExist):
        user = None
    
    if user and default_token_generator.check_token(user, token):
        if request.method == "POST":
            form = PasswordResetConfirmForm(request.POST)
            if form.is_valid():
                new_password = form.cleaned_data["new_password"]
                user.set_password(new_password)
                user.save()
                
                # Log the user in with new password
                login(
                    request,
                    user,
                    backend="django.contrib.auth.backends.ModelBackend",
                )
                
                messages.success(
                    request,
                    "Your password has been successfully reset. You are now logged in."
                )
                return _route_user_to_dashboard(user)
        else:
            form = PasswordResetConfirmForm()
        
        return render(
            request,
            "auth/password_reset_confirm.html",
            {"form": form, "valid_link": True},
        )
    else:
        messages.error(
            request,
            "Invalid or expired password reset link. Please request a new one."
        )
        return redirect("password_reset_request_email")