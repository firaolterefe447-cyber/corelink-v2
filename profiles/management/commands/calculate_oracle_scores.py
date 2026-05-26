import time
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

# Ensure this import matches where your Oracle class is actually located!
# E.g., if it's in profiles.utils import it like this:
from profiles.automatic_rating import CoreLinkOracle

User = get_user_model()


class Command(BaseCommand):
    help = "Forces the CoreLinkOracle to evaluate and score every user in the database."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("╔════════════════════════════════════════════════════════════╗"))
        self.stdout.write(self.style.WARNING("║        AWAKENING THE CORELINK ORACLE (GLOBAL SCAN)         ║"))
        self.stdout.write(self.style.WARNING("╚════════════════════════════════════════════════════════════╝"))

        # We use .iterator() so we don't blow up server memory if you have 10,000+ users
        user_ids = User.objects.filter(is_active=True).values_list('id', flat=True).iterator(chunk_size=500)

        total_evaluated = 0
        total_failed = 0
        start_time = time.time()

        for u_id in user_ids:
            try:
                # The Oracle does the heavy lifting (calculates & saves)
                CoreLinkOracle.update_user_rating(u_id)
                total_evaluated += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed on user {u_id}: {str(e)}"))
                total_failed += 1

        elapsed = round(time.time() - start_time, 2)

        self.stdout.write(self.style.SUCCESS("\n======================================================="))
        self.stdout.write(self.style.SUCCESS(f"✅ ORACLE GLOBAL SCAN COMPLETE IN {elapsed} SECONDS"))
        self.stdout.write(self.style.SUCCESS(f"✅ Successfully Evaluated: {total_evaluated} Users"))
        if total_failed > 0:
            self.stdout.write(self.style.ERROR(f"❌ Failed Evaluations: {total_failed} Users"))
        self.stdout.write(self.style.SUCCESS("=======================================================\n"))