from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from profiles.automatic_rating import CoreLinkOracle
import time

User = get_user_model()


class Command(BaseCommand):
    help = 'Periodically updates Oracle scores for all active users (designed for cron jobs)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of users to process per batch (default: 100)'
        )
        parser.add_argument(
            '--recent-only',
            action='store_true',
            help='Only update users who modified their profile in the last 24 hours'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        recent_only = options['recent_only']

        self.stdout.write(self.style.SUCCESS('🔮 ORACLE PERIODIC UPDATE STARTED'))
        
        # Build queryset
        queryset = User.objects.filter(is_active=True).select_related('portfolio')
        
        if recent_only:
            from django.utils import timezone
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(hours=24)
            queryset = queryset.filter(
                portfolio__last_signal_update__gte=cutoff
            )
            self.stdout.write(self.style.WARNING(f'⚡ Processing only recently active users (last 24h)'))
        
        total_users = queryset.count()
        self.stdout.write(f'📊 Total users to process: {total_users}')
        
        if total_users == 0:
            self.stdout.write(self.style.WARNING('No users to process.'))
            return

        # Process in batches
        processed = 0
        updated = 0
        start_time = time.time()

        for offset in range(0, total_users, batch_size):
            batch = queryset[offset:offset + batch_size]
            
            for user in batch:
                try:
                    if hasattr(user, 'portfolio'):
                        old_score = getattr(user.portfolio, 'oracle_score', 0)
                        old_rating = user.portfolio.admin_rating
                        
                        CoreLinkOracle.update_user_rating(user.id)
                        
                        # Refresh to see new values
                        user.portfolio.refresh_from_db()
                        new_score = user.portfolio.oracle_score
                        new_rating = user.portfolio.admin_rating
                        
                        if new_score != old_score or new_rating != old_rating:
                            updated += 1
                            self.stdout.write(
                                f'✅ Updated: {user.full_name} | Score: {old_score}→{new_score} | Rating: {old_rating}→{new_rating}'
                            )
                        
                        processed += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'❌ Failed for user {user.id}: {str(e)}')
                    )

            # Progress indicator
            progress = min(processed, total_users)
            self.stdout.write(f'📈 Progress: {progress}/{total_users} users processed')

        elapsed = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(
            f'🔮 ORACLE PERIODIC UPDATE COMPLETE | '
            f'Processed: {processed} | Updated: {updated} | Time: {elapsed:.2f}s'
        ))
