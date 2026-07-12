import logging
from typing import Any
import uuid
from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.text import slugify
from accounts.models import CustomUser, UniversalSocialLink, UniversalContactMethod
from core.services import optimize_standard_image
from .automatic_rating import CoreLinkOracle
from .models import (
    Company,
    CompanyMember,
    CompanyService,
    CompanyMilestone,
    CompanyNews,
)
from .models.new_unified_profile import (
    UserProfile,
    ProfileHeadline,
    Skill,
    Credential,
    PortfolioProject,
    ProjectGallery,
    WorkExperience,
    ContentPost,
    Language,
    RightNowPost,
    RightNowMedia,
    RightNowLike,
    RightNowComment,
)

logger = logging.getLogger(__name__)


def generate_unique_slug(klass, field_name, source_text):
    """
    Renamed 'full_name' argument to 'source_text' to reflect
    that it can be a company name or a person's name.
    """
    origin_slug = slugify(source_text)
    unique_slug = origin_slug

    # If slugify returns empty (e.g. source_text was special chars), use uuid
    if not unique_slug:
        unique_slug = uuid.uuid4().hex[:8]

    while klass.objects.filter(**{field_name: unique_slug}).exists():
        unique_slug = f"{origin_slug}-{uuid.uuid4().hex[:4]}"
    return unique_slug


def _trigger_oracle(user_id):
    """
    Fires the Oracle SAFELY. 
    Using transaction.on_commit ensures the Oracle only runs AFTER 
    all gallery images, skills, and related M2M data are firmly in the DB.
    """
    if user_id:
        logger.info(f"[ORACLE SIGNAL] Queued Oracle update for user_id: {user_id}")
        transaction.on_commit(lambda: _execute_oracle_update(user_id))


def _execute_oracle_update(user_id):
    """Executes the Oracle update with error handling and logging."""
    try:
        logger.info(f"[ORACLE EXECUTION] Starting IMMEDIATE Oracle update for user_id: {user_id}")
        CoreLinkOracle.update_user_rating(user_id)
        logger.info(f"[ORACLE SUCCESS] Completed IMMEDIATE Oracle update for user_id: {user_id}")
    except Exception as e:
        logger.error(f"[ORACLE ERROR] Failed to update user {user_id}: {str(e)}", exc_info=True)


# ==========================================
# 1. WATCH CORE IDENTITY & ACCOUNTS
# ==========================================
@receiver([post_save, post_delete], sender=CustomUser)
@receiver([post_save, post_delete], sender=UniversalSocialLink)
@receiver([post_save, post_delete], sender=UniversalContactMethod)
def watch_account_matrix(sender, instance, **kwargs):
    user_id = instance.id if sender == CustomUser else instance.user_id
    logger.info(f"[ORACLE SIGNAL] Account matrix signal fired: {sender.__name__} for user_id: {user_id}")
    _trigger_oracle(user_id)


# ==========================================
# 2. WATCH UNIFIED PORTFOLIO PIPELINE
# ==========================================
@receiver([post_save, post_delete], sender=UserProfile)
@receiver([post_save, post_delete], sender=ProfileHeadline)
def watch_unified_base(sender, instance, **kwargs):
    if sender == UserProfile:
        logger.info(f"[ORACLE SIGNAL] UserProfile signal fired for user_id: {instance.user_id}")
        _trigger_oracle(instance.user_id)
    elif hasattr(instance, "profile"):
        logger.info(f"[ORACLE SIGNAL] ProfileHeadline signal fired for user_id: {instance.profile.user_id}")
        _trigger_oracle(instance.profile.user_id)


@receiver([post_save, post_delete], sender=Skill)
@receiver([post_save, post_delete], sender=Credential)
@receiver([post_save, post_delete], sender=PortfolioProject)
@receiver([post_save, post_delete], sender=ProjectGallery)
@receiver([post_save, post_delete], sender=WorkExperience)
@receiver([post_save, post_delete], sender=ContentPost)
@receiver([post_save, post_delete], sender=Language)
def watch_unified_portfolio_nodes(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        logger.info(f"[ORACLE SIGNAL] {sender.__name__} signal fired for user_id: {instance.profile.user_id}")
        _trigger_oracle(instance.profile.user_id)


@receiver([post_save, post_delete], sender=RightNowPost)
@receiver([post_save, post_delete], sender=RightNowMedia)
def watch_right_now_ecosystem(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        logger.info(f"[ORACLE SIGNAL] {sender.__name__} signal fired for user_id: {instance.profile.user_id}")
        _trigger_oracle(instance.profile.user_id)


# ==========================================
# 3. WATCH COMPANY ASSETS (Corporate Override)
# ==========================================
@receiver([post_save, post_delete], sender=Company)
@receiver([post_save, post_delete], sender=CompanyMember)
@receiver([post_save, post_delete], sender=CompanyService)
@receiver([post_save, post_delete], sender=CompanyMilestone)
@receiver([post_save, post_delete], sender=CompanyNews)
def watch_company_assets(sender, instance, **kwargs):
    user_id = None
    if sender == Company:
        # Get all active members of this company
        for member in instance.members.filter(is_active=True):
            user_id = member.user_id
            logger.info(f"[ORACLE SIGNAL] {sender.__name__} signal fired for user_id: {user_id}")
            _trigger_oracle(user_id)
    elif sender == CompanyMember:
        user_id = instance.user_id
        logger.info(f"[ORACLE SIGNAL] {sender.__name__} signal fired for user_id: {user_id}")
        _trigger_oracle(user_id)
    elif hasattr(instance, "company"):
        user_id = instance.company.members.filter(is_active=True).first().user_id if instance.company.members.filter(is_active=True).exists() else None
        if user_id:
            logger.info(f"[ORACLE SIGNAL] {sender.__name__} signal fired for user_id: {user_id}")
            _trigger_oracle(user_id)


# ==============================================================================
# ASYNC SIGNAL HANDLERS (IMAGE OPTIMIZATION FOR UNIFIED MODELS)
# ==============================================================================


def _perform_optimization(instance_id: Any, model_class: type, field_name: str) -> None:
    """
    Internal helper executing the heavy image optimization logic.
    Structured to permit future extraction into a Celery task without changing caller behavior.
    """
    try:
        instance = model_class.objects.get(pk=instance_id)
        image_field = getattr(instance, field_name)

        if not image_field or not hasattr(image_field, "file"):
            return

        if not image_field.name.lower().endswith(".webp"):
            optimized = optimize_standard_image(image_field)
            if optimized:
                image_field.save(optimized.name, optimized, save=False)
                # Atomic update preventing overwrite of simultaneous text edits
                model_class.objects.filter(pk=instance.pk).update(
                    **{field_name: image_field.name}
                )
    except model_class.DoesNotExist:
        logger.warning(
            f"Optimization failed: {model_class.__name__} {instance_id} not found."
        )
    except Exception as e:
        logger.error(
            f"Image optimization error for {model_class.__name__} {instance_id}: {str(e)}"
        )


@receiver(post_save, sender=RightNowMedia)
def optimize_right_now_media(sender: Any, instance: Any, created: bool, **kwargs: Any) -> None:
    """Optimize Right Now media uploads."""
    if getattr(instance, "image", None):
        transaction.on_commit(
            lambda: _perform_optimization(instance.pk, sender, "image")
        )


@receiver(post_save, sender=ProjectGallery)
def optimize_project_gallery_media(sender: Any, instance: Any, created: bool, **kwargs: Any) -> None:
    """Optimize ProjectGallery image uploads to prevent layout issues."""
    if getattr(instance, "image", None):
        transaction.on_commit(
            lambda: _perform_optimization(instance.pk, sender, "image")
        )
