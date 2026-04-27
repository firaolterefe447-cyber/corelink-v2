import logging
from django.core.management.base import BaseCommand
from django.db import transaction

# IMPORTANT: Change to your actual app name
from profiles.models import RightNowPost, UserProfile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fixes timestamps using the safe updated_at backup.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Starting timestamp correction using safe backup...'))

        posts = RightNowPost.objects.select_related('profile').all()
        fixed_count = 0

        try:
            with transaction.atomic():
                for post in posts:
                    # 1. Grab the SAFE historical time (updated_at wasn't ruined by the migration)
                    # NOTE: If your TimeStampedModel uses a different name like 'modified', change it here:
                    true_historical_time = post.profile.updated_at

                    # 2. Fix the RightNowPost dates
                    RightNowPost.objects.filter(id=post.id).update(
                        created_at=true_historical_time,
                        updated_at=true_historical_time
                    )

                    # 3. Restore the ruined 'last_signal_update' back to its true time
                    UserProfile.objects.filter(pk=post.profile_id).update(
                        last_signal_update=true_historical_time
                    )

                    fixed_count += 1

            # Final Output
            self.stdout.write(self.style.SUCCESS(
                f'✅ Timestamp Correction Complete!\n'
                f'Restored the true historical dates from updated_at for {fixed_count} posts.'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Correction failed: {str(e)}'))
            logger.error(f"RightNowPost Timestamp Fix Error: {str(e)}")