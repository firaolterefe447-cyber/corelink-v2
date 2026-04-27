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
    VisionaryProfile,
    Project,
    Certification,
    GrowthLog,
    LearningTarget,
    VisionBlock,
    ExpertProfile,
    ExpertSkill,
    ExpertCredential,
    ExpertProject,
    ExpertExperience,
    ExpertThought,
    FounderProfile,
    Company,
    CompanyService,
    CompanyMilestone,
    CompanyNews,
    CompanySocialLink,
    CompanyContactMethod,
    ServiceGalleryImage,
    NewsGalleryImage,
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


@receiver(post_save, sender=VisionaryProfile)
@receiver(post_save, sender=ExpertProfile)
@receiver(post_save, sender=FounderProfile)
def manage_slug_generation(sender, instance, created, **kwargs):
    # Check if slug needs to be generated
    if created or not instance.slug:

        # FIX: Every profile (Visionary, Expert, AND Founder)
        # should use the person's name for their PERSONAL profile URL.
        source_text = getattr(instance.user, "full_name", None)

        if source_text:
            new_slug = generate_unique_slug(sender, "slug", source_text)

            # Update database directly to avoid re-triggering this signal
            sender.objects.filter(pk=instance.pk).update(slug=new_slug)


def _trigger_oracle(user_id):
    """Fires the Oracle asynchronously after the DB transaction is committed."""
    if user_id:
        transaction.on_commit(lambda: CoreLinkOracle.update_user_rating(user_id))


# ==========================================
# 1. WATCH CORE IDENTITY & ACCOUNTS
# ==========================================
@receiver([post_save, post_delete], sender=CustomUser)
@receiver([post_save, post_delete], sender=UniversalSocialLink)
@receiver([post_save, post_delete], sender=UniversalContactMethod)
def watch_account_matrix(sender, instance, **kwargs):
    user_id = instance.id if sender == CustomUser else instance.user_id
    _trigger_oracle(user_id)


@receiver([post_save, post_delete], sender=VisionaryProfile)
@receiver([post_save, post_delete], sender=ExpertProfile)
@receiver([post_save, post_delete], sender=FounderProfile)
def watch_base_profiles(sender, instance, **kwargs):
    # Using instance.user_id for safer access
    _trigger_oracle(instance.user_id)


# ==========================================
# 2. WATCH VISIONARY PIPELINE
# ==========================================
@receiver([post_save, post_delete], sender=Project)
@receiver([post_save, post_delete], sender=Certification)
@receiver([post_save, post_delete], sender=GrowthLog)
@receiver([post_save, post_delete], sender=LearningTarget)
@receiver([post_save, post_delete], sender=VisionBlock)
def watch_visionary_nodes(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        _trigger_oracle(instance.profile.user_id)


# ==========================================
# 3. WATCH EXPERT PIPELINE
# ==========================================
@receiver([post_save, post_delete], sender=ExpertSkill)
@receiver([post_save, post_delete], sender=ExpertCredential)
@receiver([post_save, post_delete], sender=ExpertProject)
@receiver([post_save, post_delete], sender=ExpertExperience)
@receiver([post_save, post_delete], sender=ExpertThought)
def watch_expert_nodes(sender, instance, **kwargs):
    if hasattr(instance, "profile"):
        _trigger_oracle(instance.profile.user_id)


# ==========================================
# 4. WATCH FOUNDER & COMPANY PIPELINE
# ==========================================
@receiver([post_save, post_delete], sender=Company)
@receiver([post_save, post_delete], sender=CompanyService)
@receiver([post_save, post_delete], sender=CompanyMilestone)
@receiver([post_save, post_delete], sender=CompanyNews)
@receiver([post_save, post_delete], sender=CompanySocialLink)
@receiver([post_save, post_delete], sender=CompanyContactMethod)
def watch_enterprise_nodes(sender, instance, **kwargs):
    # Locate the root Company
    if sender == Company:
        company = instance
    elif hasattr(instance, "company"):
        company = instance.company
    else:
        company = None

    # If the company's data changes, recalculate all active Founders attached to it
    if company:
        for member in company.members.filter(is_active=True):
            _trigger_oracle(member.user_id)


# ==============================================================================
# 5. ASYNC SIGNAL HANDLERS (IMAGE OPTIMIZATION)
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


@receiver(post_save, sender=Company)
@receiver(post_save, sender=ServiceGalleryImage)
@receiver(post_save, sender=CompanyNews)
@receiver(post_save, sender=NewsGalleryImage)
def optimize_images_async_placeholder(
    sender: Any, instance: Any, created: bool, **kwargs: Any
) -> None:
    """
    Intercepts Media uploads to run optimizations post-commit safely.
    (Removed FounderProfile target fields as part of the Name Section removal requirements).
    """
    target_fields = []

    if sender in [ServiceGalleryImage, NewsGalleryImage]:
        target_fields.append("image")
    elif sender == CompanyNews:
        target_fields.append("cover_image")
    elif sender == Company:
        target_fields.append("cover_image")
        target_fields.append("logo")

    for field in target_fields:
        if getattr(instance, field, None):
            transaction.on_commit(
                lambda f=field: _perform_optimization(instance.pk, sender, f)
            )
