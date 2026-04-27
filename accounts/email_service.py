import os
import logging
import secrets
import json
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.utils import timezone
from django.core import signing
from django.core.signing import SignatureExpired, BadSignature
from django.contrib.auth.hashers import make_password, check_password
from django.urls import reverse
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class BrevoEmailService:
    TOKEN_SALT = "accounts.email_verification"
    USER_SAFE_EMAIL_ERROR = "We couldn't send the verification code right now. Please try again in a few minutes."

    def __init__(self):
        # 1. Retrieve the API key from environment variables
        api_key = os.environ.get("BREVO_API_KEY")

        if not api_key:
            logger.error("Missing BREVO_API_KEY environment variable.")
            self.api_instance = None
            return

        # 2. Configure the API client
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = api_key

        # 3. Initialize the Transactional Emails API instance
        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        # 4. Define the sender parameters
        self.sender = {
            "email": os.environ.get("SENDER_EMAIL", "donotreply@corelink.et"),
            "name": os.environ.get("SENDER_NAME", "CoreLink"),
        }

    def send_email(self, to_email, subject, html_content, to_name=None):
        if not self.api_instance:
            logger.error("Brevo API instance not initialized. Check BREVO_API_KEY.")
            return {
                "success": False,
                "error": "Email service is currently unavailable.",
            }

        # 5. Define the email parameters
        to = [{"email": to_email, "name": to_name or ""}]

        # 6. Construct the send object
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=to, sender=self.sender, subject=subject, html_content=html_content
        )

        # 7. Execute the request
        try:
            api_response = self.api_instance.send_transac_email(send_smtp_email)
            return {"success": True, "message_id": api_response.message_id}
        except ApiException as e:
            logger.error(f"Brevo API Error: status={e.status} body={e.body}")
            provider_message = "Email provider rejected the request."
            if e.body:
                try:
                    parsed = json.loads(e.body)
                    provider_message = parsed.get("message", provider_message)
                except Exception:
                    pass
            return {
                "success": False,
                "error": provider_message,
            }
        except Exception as e:
            logger.exception(f"Unexpected error sending email to {to_email}: {str(e)}")
            return {"success": False, "error": "An unexpected error occurred."}

    def generate_otp(self):
        return "".join(secrets.choice("0123456789") for _ in range(6))

    def send_verification_email(self, user, request, email=None):
        otp = self.generate_otp()
        target_email = email or user.email

        # 1. Store the OTP securely (hashed)
        user.email_otp = make_password(otp)
        user.email_otp_created_at = timezone.now()
        user.save(update_fields=["email_otp", "email_otp_created_at"])

        # 2. Generate an automatic verification link
        token = self.generate_verification_token(user, target_email)
        verify_url = request.build_absolute_uri(
            reverse("verify_email_token", kwargs={"token": token})
        )

        html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                    <h2 style="color: #0A66C2;">Welcome to CoreLink, {user.full_name}!</h2>
                    <p>To complete your email verification, please use the following 6-digit code:</p>
                    <div style="background-color: #f4f4f4; padding: 20px; text-align: center; border-radius: 5px; margin: 20px 0;">
                        <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #0A66C2;">{otp}</span>
                    </div>
                    <p style="text-align: center;">OR</p>
                    <div style="text-align: center; margin: 20px 0;">
                        <a href="{verify_url}" style="background-color: #0A66C2; color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">Verify Automatically</a>
                    </div>
                    <p>This code and link will expire in 15 minutes.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="font-size: 12px; color: #999;">Next time, you can login with your email once it's verified!</p>
                </div>
            </body>
            </html>
        """

        result = self.send_email(
            to_email=target_email,
            to_name=user.full_name,
            subject=f"{otp} is your CoreLink Verification Code",
            html_content=html_content,
        )

        if result["success"]:
            return True, None
        else:
            logger.warning(
                "Verification email delivery failed for user_id=%s target=%s provider_error=%s",
                user.pk,
                target_email,
                result.get("error", "unknown"),
            )
            return False, self.USER_SAFE_EMAIL_ERROR

    def send_welcome_email(self, user):
        if not user.email:
            return False, "User has no email address."

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

        result = self.send_email(
            to_email=user.email,
            to_name=user.full_name,
            subject="Welcome to CoreLink",
            html_content=html_content,
        )

        if result["success"]:
            return True, None
        return False, result.get("error", "Failed to send welcome email.")

    def verify_otp(self, user, otp, max_age_minutes=15):
        if not user.email_otp or not check_password(otp, user.email_otp):
            return False

        if not user.email_otp_created_at:
            return False

        elapsed_time = timezone.now() - user.email_otp_created_at
        if elapsed_time.total_seconds() > max_age_minutes * 60:
            return False

        return True

    def generate_verification_token(self, user, email):
        payload = {
            "uid": str(user.pk),
            "email": email,
            "purpose": "email_verification",
        }
        return signing.dumps(payload, salt=self.TOKEN_SALT)

    def verify_token(self, token, max_age=900):
        # Default max_age set to 900 seconds (15 minutes) to match OTP expiration
        try:
            payload = signing.loads(token, salt=self.TOKEN_SALT, max_age=max_age)

            if payload.get("purpose") != "email_verification":
                return None

            if not payload.get("uid") or not payload.get("email"):
                return None

            return payload
        except (SignatureExpired, BadSignature):
            return None
