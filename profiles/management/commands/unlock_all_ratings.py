from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from profiles.models.new_unified_profile import UserProfile

User = get_user_model()


class Command(BaseCommand):
    help = "Unlocks all user ratings by setting is_rating_locked to False for all profiles."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("╔════════════════════════════════════════════════════════════╗"))
        self.stdout.write(self.style.WARNING("║           UNLOCKING ALL USER RATINGS                         ║"))
        self.stdout.write(self.style.WARNING("╚════════════════════════════════════════════════════════════╝"))

        updated_count = UserProfile.objects.filter(is_rating_locked=True).update(is_rating_locked=False)

        self.stdout.write(self.style.SUCCESS(f"\n✅ Successfully unlocked {updated_count} user profiles"))
        self.stdout.write(self.style.SUCCESS("✅ Oracle can now auto-update all ratings"))
        self.stdout.write(self.style.SUCCESS("=======================================================\n"))
