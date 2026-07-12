"""
Management command to optimize all existing project gallery images.
This handles images uploaded before the optimization signal was implemented。
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from profiles.models.new_unified_profile import ProjectGallery
from core.services import optimize_standard_image
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Optimize all existing project gallery images to prevent layout issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be optimized without actually processing',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of images to process per batch (default: 100)',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        batch_size = options.get('batch_size', 100)

        self.stdout.write(self.style.WARNING('Starting project gallery image optimization...'))

        # Get all project gallery images that need optimization
        all_images = ProjectGallery.objects.filter(
            image__isnull=False
        )

        total_count = all_images.count()
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('No images need optimization. All are already WebP.'))
            return

        self.stdout.write(f'Found {total_count} images to optimize.')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
            for img in all_images[:10]:  # Show first 10
                self.stdout.write(f'  - {img.image.name} ({img.image.size if img.image else "N/A"} bytes)')
            if total_count > 10:
                self.stdout.write(f'  ... and {total_count - 10} more')
            return

        # Process in batches
        processed = 0
        skipped = 0
        errors = 0

        for offset in range(0, total_count, batch_size):
            batch = all_images[offset:offset + batch_size]
            
            self.stdout.write(f'Processing batch {offset + 1}-{min(offset + batch_size, total_count)} of {total_count}...')

            for gallery_item in batch:
                try:
                    if not gallery_item.image or not gallery_item.image.name:
                        skipped += 1
                        continue

                    # Skip if already WebP
                    if gallery_item.image.name.lower().endswith('.webp'):
                        skipped += 1
                        continue

                    # Optimize the image
                    optimized = optimize_standard_image(gallery_item.image)
                    
                    if optimized:
                        # Save the optimized image
                        gallery_item.image.save(optimized.name, optimized, save=False)
                        # Update the database record
                        ProjectGallery.objects.filter(pk=gallery_item.pk).update(
                            image=gallery_item.image.name
                        )
                        processed += 1
                        self.stdout.write(f'  [OK] Optimized: {gallery_item.image.name}')
                    else:
                        skipped += 1
                        self.stdout.write(f'  [SKIP] Skipped (no optimization needed): {gallery_item.image.name}')

                except Exception as e:
                    errors += 1
                    logger.error(f"Error optimizing image {gallery_item.image.name}: {str(e)}")
                    self.stdout.write(self.style.ERROR(f'  [ERROR] Error: {gallery_item.image.name} - {str(e)}'))

        # Summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('Optimization Complete!'))
        self.stdout.write(f'Total images found: {total_count}')
        self.stdout.write(f'Successfully optimized: {processed}')
        self.stdout.write(f'Skipped: {skipped}')
        self.stdout.write(f'Errors: {errors}')
        self.stdout.write('=' * 50)
