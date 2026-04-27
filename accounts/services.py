from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def generate_corelink_id(role: str) -> str:
    """
    Sovereign Logic: Generates [PREFIX]-[YEAR]-[SEQUENCE].
    Example: EXP-26-0042
    """

    # --- CRITICAL FIX: BREAK CIRCULAR IMPORT ---
    # We import IDSequence here instead of at the top of the file
    from .models import IDSequence
    # -------------------------------------------

    # 1. Map Role to Prefix
    prefix_map = {
        'EXPERT': 'EXP',
        'VISIONARY': 'VIS',
        'STUDENT': 'VIS',  # Mapping student to VIS prefix
        'FOUNDER': 'FND',
        'ADMIN': 'ADM'
    }

    prefix = prefix_map.get(role.upper(), 'USR')
    current_year = int(timezone.now().strftime('%y'))

    try:
        with transaction.atomic():
            # select_for_update() locks the row so no two users get the same ID
            sequence, created = IDSequence.objects.select_for_update().get_or_create(
                prefix=prefix,
                defaults={'year': current_year, 'last_number': 0}
            )

            # Year Reset Logic
            if sequence.year != current_year:
                sequence.year = current_year
                sequence.last_number = 0

            # Increment and Save
            sequence.last_number += 1
            sequence.save()

            return f"{prefix}-{current_year}-{sequence.last_number:04d}"

    except Exception as e:
        logger.error(f"Critical ID Generation Failure: {e}")
        import uuid
        return f"{prefix}-ERR-{uuid.uuid4().hex[:4].upper()}"