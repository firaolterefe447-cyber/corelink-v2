"""
Django management command to migrate Service and ServiceGallery data 
from profiles app to the dedicated services app.

This script is designed to be safe, interactive, and provide clear feedback
during the migration process.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection
from django.utils import timezone
from django.utils.text import Truncator
from django.conf import settings
from django.db.models import Count
import sys
from typing import Optional


class Command(BaseCommand):
    help = 'Migrate Service and ServiceGallery data from profiles app to services app'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Simulate the migration without actually making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            dest='force',
            help='Skip confirmation prompts (use with caution)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            dest='batch_size',
            default=100,
            help='Number of records to process per batch (default: 100)',
        )

    def print_header(self, text: str):
        """Print a formatted header."""
        self.stdout.write(self.style.SUCCESS(f"\n{'=' * 70}"))
        self.stdout.write(self.style.SUCCESS(f"  {text}"))
        self.stdout.write(self.style.SUCCESS(f"{'=' * 70}\n"))

    def print_section(self, text: str):
        """Print a formatted section header."""
        self.stdout.write(self.style.HTTP_INFO(f"\n--- {text} ---"))

    def print_success(self, text: str):
        """Print success message."""
        self.stdout.write(self.style.SUCCESS(f"[OK] {text}"))

    def print_warning(self, text: str):
        """Print warning message."""
        self.stdout.write(self.style.WARNING(f"[WARN] {text}"))

    def print_error(self, text: str):
        """Print error message."""
        self.stdout.write(self.style.ERROR(f"[ERROR] {text}"))

    def print_info(self, text: str):
        """Print info message."""
        self.stdout.write(self.style.HTTP_INFO(f"[INFO] {text}"))

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)
        batch_size = options.get('batch_size', 100)

        self.print_header("SERVICE MIGRATION TOOL")

        # Check if source models exist
        try:
            from profiles.models import Service as ProfileService, ServiceGallery as ProfileServiceGallery
        except ImportError as e:
            self.print_error(f"Cannot import source models from profiles app: {e}")
            raise CommandError("Source models not found. Make sure profiles app is installed.")

        # Check if destination models exist
        try:
            from services.models import Service as NewService, ServiceGallery as NewServiceGallery
        except ImportError as e:
            self.print_error(f"Cannot import destination models from services app: {e}")
            raise CommandError("Destination models not found. Make sure services app is installed.")

        # Check if tables exist
        self.print_section("Checking Database Tables")
        tables = connection.introspection.table_names()
        
        source_service_table = 'profiles_service'
        source_gallery_table = 'profiles_servicegallery'
        dest_service_table = 'services_service'
        dest_gallery_table = 'services_servicegallery'

        if source_service_table not in tables:
            self.print_warning(f"Source table '{source_service_table}' does not exist. Nothing to migrate.")
            return

        if dest_service_table not in tables:
            self.print_error(f"Destination table '{dest_service_table}' does not exist. Run migrations first.")
            raise CommandError("Run 'python manage.py migrate services' to create the tables.")

        # Count existing data
        self.print_section("Analyzing Data")
        
        source_service_count = ProfileService.objects.count()
        source_gallery_count = ProfileServiceGallery.objects.count()
        dest_service_count = NewService.objects.count()
        dest_gallery_count = NewServiceGallery.objects.count()

        self.print_info(f"Source Services: {source_service_count}")
        self.print_info(f"Source Gallery Images: {source_gallery_count}")
        self.print_info(f"Destination Services (existing): {dest_service_count}")
        self.print_info(f"Destination Gallery Images (existing): {dest_gallery_count}")

        if source_service_count == 0:
            self.print_warning("No services found in source. Nothing to migrate.")
            return

        if dest_service_count > 0:
            self.print_warning(f"Destination already has {dest_service_count} services.")
            if not force:
                response = input("Continue with migration? This may create duplicates. (yes/no): ")
                if response.lower() not in ['yes', 'y']:
                    self.print_info("Migration cancelled by user.")
                    return

        # Show preview
        self.print_section("Migration Preview")
        self.print_info(f"Services to migrate: {source_service_count}")
        self.print_info(f"Gallery images to migrate: {source_gallery_count}")
        self.print_info(f"Batch size: {batch_size}")
        
        if dry_run:
            self.print_warning("DRY RUN MODE - No changes will be made to the database")

        # Confirmation
        if not force:
            self.print_section("Confirmation Required")
            response = input("Proceed with migration? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                self.print_info("Migration cancelled by user.")
                return

        # Execute migration
        self.print_header("STARTING MIGRATION")
        
        try:
            with transaction.atomic():
                if dry_run:
                    self.print_warning("Dry run - skipping actual migration")
                    # Just simulate the migration
                    self._simulate_migration(ProfileService, ProfileServiceGallery, batch_size)
                else:
                    self._execute_migration(
                        ProfileService, ProfileServiceGallery,
                        NewService, NewServiceGallery,
                        batch_size
                    )
                    
                    if not force:
                        # Rollback if not forced (for safety)
                        raise CommandError("Migration was successful but rolled back for safety. Use --force to commit.")

        except Exception as e:
            self.print_error(f"Migration failed: {str(e)}")
            raise CommandError(f"Migration error: {e}")

        self.print_header("MIGRATION COMPLETE")

    def _simulate_migration(self, ProfileService, ProfileServiceGallery, batch_size):
        """Simulate migration without actually writing to database."""
        self.print_section("Simulating Service Migration")
        
        services = ProfileService.objects.all().select_related('profile')
        total = services.count()
        processed = 0
        
        for service in services.iterator(chunk_size=batch_size):
            processed += 1
            if processed % 10 == 0 or processed == total:
                self.print_info(f"Processed {processed}/{total} services")
        
        self.print_success(f"Simulated migration of {total} services")
        
        # Simulate gallery migration
        gallery_count = ProfileServiceGallery.objects.count()
        self.print_success(f"Simulated migration of {gallery_count} gallery images")

    def _execute_migration(self, ProfileService, ProfileServiceGallery, 
                          NewService, NewServiceGallery, batch_size):
        """Execute the actual migration."""
        # Create a mapping of old service IDs to new service IDs
        id_mapping = {}
        
        # Migrate Services
        self.print_section("Migrating Services")
        
        services = ProfileService.objects.all().select_related('profile')
        total = services.count()
        processed = 0
        skipped = 0
        
        for old_service in services.iterator(chunk_size=batch_size):
            # Check if service already exists (by ID or profile+title)
            existing = NewService.objects.filter(
                id=old_service.id
            ).first()
            
            if existing:
                self.print_warning(f"Service {old_service.id} already exists, skipping")
                skipped += 1
                id_mapping[old_service.id] = existing.id
                processed += 1
                continue
            
            # Create new service
            new_service = NewService(
                id=old_service.id,
                profile=old_service.profile,
                title=old_service.title,
                description=old_service.description,
                is_active=old_service.is_active,
                order=old_service.order,
                created_at=old_service.created_at,
                updated_at=old_service.updated_at
            )
            new_service.save()
            
            id_mapping[old_service.id] = new_service.id
            
            processed += 1
            if processed % 10 == 0 or processed == total:
                self.print_info(f"Migrated {processed}/{total} services")
        
        self.print_success(f"Migrated {processed - skipped} services (skipped {skipped} duplicates)")

        # Migrate ServiceGallery
        self.print_section("Migrating Service Gallery Images")
        
        gallery_items = ProfileServiceGallery.objects.all().select_related('service')
        total = gallery_items.count()
        processed = 0
        skipped = 0
        
        for old_gallery in gallery_items.iterator(chunk_size=batch_size):
            # Check if gallery item already exists
            existing = NewServiceGallery.objects.filter(
                id=old_gallery.id
            ).first()
            
            if existing:
                self.print_warning(f"Gallery item {old_gallery.id} already exists, skipping")
                skipped += 1
                processed += 1
                continue
            
            # Get the new service ID from mapping
            new_service_id = id_mapping.get(old_gallery.service_id)
            
            if not new_service_id:
                self.print_warning(f"Service {old_gallery.service_id} not found in mapping, skipping gallery item")
                skipped += 1
                processed += 1
                continue
            
            # Create new gallery item
            new_gallery = NewServiceGallery(
                id=old_gallery.id,
                service_id=new_service_id,
                image=old_gallery.image,
                caption=old_gallery.caption,
                order=old_gallery.order
            )
            new_gallery.save()
            
            processed += 1
            if processed % 10 == 0 or processed == total:
                self.print_info(f"Migrated {processed}/{total} gallery images")
        
        self.print_success(f"Migrated {processed - skipped} gallery images (skipped {skipped} duplicates)")

        # Final summary
        self.print_section("Migration Summary")
        self.print_success(f"Services migrated: {processed - skipped}")
        self.print_info(f"Services skipped (duplicates): {skipped}")
        self.print_success(f"Gallery images migrated: {processed - skipped}")
        self.print_info(f"Gallery images skipped (duplicates): {skipped}")
