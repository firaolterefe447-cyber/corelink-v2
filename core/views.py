# core/views.py

# ==========================================
# 1. STANDARD LIBRARY IMPORTS
# ==========================================
import json
import logging
import secrets
import random  # Kept for safety if used in other views
import string  # Kept for safety if used in other views
import threading  # Kept for safety if used in other views

# ==========================================
# 2. THIRD-PARTY IMPORTS
# ==========================================
import requests

# ==========================================
# 3. DJANGO IMPORTS
# ==========================================
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import close_old_connections
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt

# ==========================================
# 4. INITIALIZATION
# ==========================================
# Initialize logger for debugging and define the User model
logger = logging.getLogger(__name__)
User = get_user_model()


# ==========================================
# 5. STANDARD WEB VIEWS
# ==========================================
from django.shortcuts import render
from django.db.models import F, Value, FloatField, Case, When
from django.db.models.functions import Cast, Coalesce
from accounts.models import CustomUser

from django.shortcuts import render
from django.db.models import F, Value, FloatField, Case, When
from django.db.models.functions import Cast, Coalesce


from django.db.models.functions import Cast, Coalesce
from django.db.models import Value, FloatField, Case, When, F
from django.shortcuts import render
# Make sure you import CustomUser if it's not already in the file

from django.db.models import F, Value, Case, When, FloatField
from django.db.models.functions import Cast, Coalesce
from django.shortcuts import render


def index_view(request):
    """
    Fetches curated users for the landing page.
    Fallback: Shows 8 newest if none are selected by admin.
    """
    # Base Query: Active, Public, Non-Admin
    base_users = CustomUser.objects.filter(
        is_active=True, is_public=True, is_nexus_visible=True
    ).exclude(role='ADMIN')

    # 1. Hero Avatars Logic
    selected_avatars = base_users.filter(is_hero_avatar_selected=True)

    if selected_avatars.exists():
        # If admin selected specific people, show them (can be any number)
        hero_avatars = selected_avatars.only('avatar', 'full_name', 'id').order_by('-created_at')
    else:
        # Fallback: If nothing selected, show the 8 newest professionals
        hero_avatars = base_users.only('avatar', 'full_name', 'id').order_by('-created_at')[:8]

    # 2. Home Page Top User (Single featured user)
    top_hero_user = base_users.filter(home_page_top=True).select_related('portfolio').prefetch_related('portfolio__headlines').first()

    # 3. Talent Network Profile Cards
    network_profiles = base_users.select_related(
        'portfolio'
    ).prefetch_related(
        'company_memberships__company'
    ).annotate(
        admin_score=Cast(Coalesce('portfolio__admin_rating', Value(0)) * 10, FloatField()),
        score_avatar=Case(When(avatar='', then=0), default=20, output_field=FloatField()),
        score_verified=Case(When(is_verified=True, then=15), default=0, output_field=FloatField()),
    ).annotate(
        total_quality=F('admin_score') + F('score_avatar') + F('score_verified')
    ).order_by('-is_home_profile_selected', '-total_quality')[:4]

    return render(request, 'index.html', {
        'hero_avatars': hero_avatars,
        'top_hero_user': top_hero_user,
        'featured_profiles': network_profiles
    })
# ==========================================
# 6. TELEGRAM BOT HELPER FUNCTIONS
# ==========================================
def send_telegram_message(chat_id, text, reply_markup=None):
    """
    Helper function to send a professionally formatted HTML message to a Telegram user.
    Includes a 5-second timeout to ensure the Django server never hangs.
    """
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }

    if reply_markup:
        payload['reply_markup'] = reply_markup

    try:
        # Timeout ensures our webhook stays lightning fast even if Telegram is slow
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code >= 400:
            logger.error(f"Telegram API Error ({response.status_code}): {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Telegram Network/Timeout Error: {e}")
    except Exception as e:
        logger.exception(f"Unexpected Telegram Delivery Error: {e}")


# ==========================================
# 7. TELEGRAM WEBHOOK VIEW
# ==========================================
@csrf_exempt
def telegram_webhook(request):
    """
    Main webhook receiver for the CoreLink Telegram Bot.
    Synchronous execution for guaranteed delivery and server stability.
    """
    # Reject anything that isn't a POST request securely
    if request.method != 'POST':
        return HttpResponse("OK")

    try:
        data = json.loads(request.body)

        # 🛑 SAFETY FIX: Telegram sends different update types (like 'edited_message').
        # If it's not a standard 'message', we safely ignore it to prevent crashes.
        message = data.get('message')
        if not message:
            return HttpResponse("OK")

        chat_id = message.get('chat', {}).get('id')
        from_user_id = message.get('from', {}).get('id')
        text = message.get('text', '').strip()

        # Ignore system messages that lack a chat_id
        if not chat_id:
            return HttpResponse("OK")

        # ---------------------------------------------------------
        # A. INITIAL OUTREACH: Professional & Explicit Instructions
        # ---------------------------------------------------------
        if text in ['/start', '/help']:
            keyboard = {
                'keyboard': [[{'text': "📱 Verify My Phone Number", 'request_contact': True}]],
                'resize_keyboard': True,
                'one_time_keyboard': True
            }

            welcome_text = (
                "<b>Welcome to the CoreLink Community Bot.</b>\n\n"
                "To securely reset your 4-digit platform PIN, we must verify your identity.\n\n"
                "<b>Important Requirement:</b>\n"
                "For security purposes, the phone number attached to this Telegram account <b>must exactly match</b> the phone number you registered with on CoreLink. "
                "If you are using a different number, this automated reset will not work.\n\n"
                "Please share your contact details using the button below to proceed."
            )
            send_telegram_message(chat_id, welcome_text, reply_markup=keyboard)

        # ---------------------------------------------------------
        # B. VERIFICATION & PIN RESET (Strict 4-Digit Logic)
        # ---------------------------------------------------------
        elif 'contact' in message:
            contact = message['contact']
            contact_user_id = contact.get('user_id')
            phone = contact.get('phone_number', '').replace('+', '').replace(' ', '')

            # Enforce strict contact ownership (Prevent identity spoofing)
            if from_user_id != contact_user_id:
                send_telegram_message(
                    chat_id,
                    "<b>Security Notice:</b>\nIdentity verification failed. You may only authenticate using the phone number registered to your own Telegram account."
                )
                return HttpResponse("OK")

            try:
                # Match user by last 9 digits (accommodates standard Ethiopian numbering formats)
                user = User.objects.get(phone_number__endswith=phone[-9:])

                # Generate a cryptographically secure 4-digit PIN (1000-9999)
                new_pass = str(secrets.randbelow(9000) + 1000)

                # Update the database securely
                user.set_password(new_pass)
                user.save()

                # Safely extract the user's actual name to personalize the message
                display_name = user.get_full_name().strip()
                if not display_name:
                    # Fallback to first name or username if full name is completely blank
                    display_name = getattr(user, 'first_name', '').strip() or getattr(user, 'username', 'User')

                success_text = (
                    f"<b>Verification Successful.</b>\n\n"
                    f"Welcome back to CoreLink, <b>{display_name}</b>.\n\n"
                    f"Your new 4-digit login PIN is:\n"
                    f"<code>{new_pass}</code> (Tap to copy)\n\n"
                    f"Please keep this password safe so that you can use it anytime you want to log in to the platform."
                )

                inline_keyboard = {
                    'remove_keyboard': True,
                    'inline_keyboard': [[
                        {'text': "Access CoreLink Portal", 'url': "https://corelink.et/login/"}
                    ]]
                }

                send_telegram_message(chat_id, success_text, reply_markup=inline_keyboard)

            except User.DoesNotExist:
                send_telegram_message(
                    chat_id,
                    "<b>Account Not Found.</b>\n\n"
                    "We could not match this Telegram phone number with an active CoreLink member profile. "
                    "Please ensure you are using the exact phone number associated with your registration.\n\n"
                    "If you require further assistance, please contact community administration."
                )
            except User.MultipleObjectsReturned:
                logger.error(f"Data Integrity Issue: Multiple accounts for phone {phone}")
                send_telegram_message(
                    chat_id,
                    "<b>System Notice:</b>\nWe detected a conflict with your contact information. Please reach out to the platform administrators to resolve this."
                )

        # ---------------------------------------------------------
        # C. UNRECOGNIZED INPUT (Handles Random Chat)
        # ---------------------------------------------------------
        else:
            send_telegram_message(
                chat_id,
                "This automated service is reserved for password resets.\n\nPlease type /start to begin the verification process."
            )

    except Exception as e:
        logger.error(f"Webhook Receiver Error: {e}", exc_info=True)
        # Graceful degradation: inform the user politely instead of staying silent.
        if 'chat_id' in locals() and chat_id:
            send_telegram_message(
                chat_id,
                "<b>Service Update:</b>\nThe system is currently processing updates or experiencing high load. Please try again shortly."
            )

    # ALWAYS return a 200 OK to Telegram to stop it from endlessly retrying/crashing
    return HttpResponse("OK")