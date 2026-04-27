import logging
import uuid
from typing import Any

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.services import optimize_avatar, optimize_cover_image
from .user import CustomUser

logger = logging.getLogger(__name__)


def _process_user_images(user_pk: uuid.UUID) -> None:
    try:
        user = CustomUser.objects.get(pk=user_pk)

        if (
            user.avatar
            and hasattr(user.avatar, "file")
            and not user.avatar.name.lower().endswith(".webp")
        ):
            optimized = optimize_avatar(user.avatar)
            if optimized:
                user.avatar.save(optimized.name, optimized, save=False)
                CustomUser.objects.filter(pk=user_pk).update(avatar=user.avatar.name)

        if (
            user.cover_image
            and hasattr(user.cover_image, "file")
            and not user.cover_image.name.lower().endswith(".webp")
        ):
            optimized = optimize_cover_image(user.cover_image)
            if optimized:
                user.cover_image.save(optimized.name, optimized, save=False)
                CustomUser.objects.filter(pk=user_pk).update(
                    cover_image=user.cover_image.name
                )

    except CustomUser.DoesNotExist:
        logger.warning(f"Image optimization failed: User {user_pk} not found.")
    except Exception as e:
        logger.error(f"Image optimization error for User {user_pk}: {e}")


@receiver(post_save, sender=CustomUser)
def trigger_image_optimization(
    sender: Any,
    instance: CustomUser,
    created: bool,
    **kwargs: Any,
) -> None:
    if instance.avatar or instance.cover_image:
        transaction.on_commit(lambda: _process_user_images(instance.pk))
