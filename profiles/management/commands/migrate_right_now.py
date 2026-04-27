import logging
from django.core.management.base import BaseCommand
from django.db import transaction

# IMPORTANT: Change 'portfolio.models' to your actual app name if different!
from profiles.models import UserProfile, RightNowPost

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Safely migrates legacy UserProfile status fields into the new RightNowPost architecture.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Starting data migration to RightNowPost...'))

        profiles = UserProfile.objects.all()
        total_profiles = profiles.count()

        created_count = 0
        skipped_count = 0

        # We wrap the entire operation in a single database transaction.
        # If anything fails, the database rolls back to its exact previous state.
        try:
            with transaction.atomic():
                for profile in profiles:
                    # IDEMPOTENCY CHECK:
                    # If this user already has an active RightNowPost, skip them.
                    # This means you can safely run this script multiple times without duplicating data.
                    if RightNowPost.objects.filter(profile=profile, is_active_focus=True).exists():
                        skipped_count += 1
                        continue

                    # Determine if they actually typed a custom mission, or if it's just defaults
                    has_custom_mission = bool(profile.current_mission and profile.current_mission.strip())

                    # Create the new feed post based on legacy data
                    RightNowPost.objects.create(
                        profile=profile,

                        # --- THE EXACT 3 FIELDS BEING COPIED ---
                        current_search=profile.current_search,
                        collaboration_status=profile.collaboration_status,
                        body_narrative=profile.current_mission if has_custom_mission else "",

                        # Set an automatic title if they wrote a mission, otherwise leave blank
                        title="Current Focus Update" if has_custom_mission else "",

                        # State Flags
                        is_active_focus=True,
                        is_published=True  # Pushes their historical status to the feed
                    )

                    created_count += 1

            # Final Output
            self.stdout.write(self.style.SUCCESS(
                f'✅ Migration Complete!\n'
                f'Total Profiles Scanned: {total_profiles}\n'
                f'RightNowPosts Created: {created_count}\n'
                f'Profiles Skipped (Already Migrated): {skipped_count}'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Migration failed: {str(e)}'))
            logger.error(f"RightNowPost Migration Error: {str(e)}")