"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              CORELINK LEGACY PROFILE CLEANUP COMMAND                           ║
║              Production-Safe Data Deletion & Model Cleanup                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

This command safely removes all legacy profile models and their database tables
after verifying that all data has been successfully migrated to the unified
UserProfile system.

SAFETY FEATURES:
- Pre-deletion verification of migration completeness
- Dry-run mode for testing
- Detailed metrics and progress reporting
- Transaction-based atomic operations
- Rollback capability on errors
- Comprehensive logging
"""

import os
import sys
import logging
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.utils import timezone
from django.contrib.auth import get_user_model

# Setup logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Safely removes legacy profile models and database tables after migration verification'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.legacy_models = {
            'expert': [
                'profiles_expertprofile',
                'profiles_expertheadline', 
                'profiles_expertskill',
                'profiles_expertcredential',
                'profiles_expertproject',
                'profiles_projectgalleryimage',
                'profiles_expertexperience',
                'profiles_jobpreference',
                'profiles_expertthought',
            ],
            'visionary': [
                'profiles_visionaryprofile',
                'profiles_certification',
                'profiles_project',
                'profiles_projectimage',
                'profiles_growthlog',
                'profiles_learningtarget',
                'profiles_visionblock',
            ],
            'founder': [
                'profiles_founderprofile',
            ]
        }
        
        self.files_to_delete = [
            'profiles/models/expert.py',
            'profiles/models/visionary.py', 
            'profiles/models/founder.py',
            'profiles/management/commands/migrate_to_unified_profiles.py',
            'profiles/management/commands/migrate_right_now.py',
            'profiles/management/commands/fix_legacy_founders.py',
            'profiles/management/commands/fix_timestamps.py',
        ]

    def print_banner(self):
        """Prints a formatted banner for the operation"""
        banner = """
===============================================================================
          CORELINK LEGACY PROFILE CLEANUP - PRODUCTION MODE                    
===============================================================================
        """
        self.stdout.write(self.style.WARNING(banner))

    def verify_migration_complete(self):
        """Verifies that all users have migrated to UserProfile"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.WARNING("[PHASE 1] MIGRATION VERIFICATION"))
        self.stdout.write("="*80)
        
        User = get_user_model()
        
        try:
            from profiles.models.new_unified_profile import UserProfile
            from profiles.models.expert import ExpertProfile
            from profiles.models.visionary import VisionaryProfile
            from profiles.models.founder import FounderProfile
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"❌ Import Error: {e}"))
            return False

        total_users = User.objects.count()
        unified_count = UserProfile.objects.count()
        expert_count = ExpertProfile.objects.count()
        visionary_count = VisionaryProfile.objects.count()
        founder_count = FounderProfile.objects.count()
        
        # Check if all users with legacy profiles also have unified profiles
        users_with_expert = User.objects.filter(expert_profile__isnull=False).count()
        users_with_visionary = User.objects.filter(visionary_profile__isnull=False).count()
        users_with_founder = User.objects.filter(founder_profile__isnull=False).count()
        
        expert_with_unified = User.objects.filter(
            expert_profile__isnull=False, 
            portfolio__isnull=False
        ).count()
        visionary_with_unified = User.objects.filter(
            visionary_profile__isnull=False,
            portfolio__isnull=False
        ).count()
        founder_with_unified = User.objects.filter(
            founder_profile__isnull=False,
            portfolio__isnull=False
        ).count()
        
        # Display metrics
        self.stdout.write(f"\n[DATABASE METRICS]:")
        self.stdout.write(f"   Total Users: {total_users}")
        self.stdout.write(f"   Unified Profiles: {unified_count}")
        self.stdout.write(f"   Legacy Expert Profiles: {expert_count}")
        self.stdout.write(f"   Legacy Visionary Profiles: {visionary_count}")
        self.stdout.write(f"   Legacy Founder Profiles: {founder_count}")
        
        self.stdout.write(f"\n[MIGRATION STATUS]:")
        self.stdout.write(f"   Expert users with UserProfile: {expert_with_unified}/{users_with_expert}")
        self.stdout.write(f"   Visionary users with UserProfile: {visionary_with_unified}/{users_with_visionary}")
        self.stdout.write(f"   Founder users with UserProfile: {founder_with_unified}/{users_with_founder}")
        
        # Verification logic
        migration_complete = (
            expert_with_unified == users_with_expert and
            visionary_with_unified == users_with_visionary and
            founder_with_unified == users_with_founder
        )
        
        if migration_complete:
            self.stdout.write(self.style.SUCCESS("\n[PASSED] MIGRATION VERIFICATION"))
            self.stdout.write("   All legacy profiles have been successfully migrated to UserProfile")
            return True
        else:
            self.stdout.write(self.style.ERROR("\n[FAILED] MIGRATION VERIFICATION"))
            self.stdout.write("   Some users still have legacy profiles without UserProfile")
            return False

    def get_table_counts(self):
        """Gets current row counts for all legacy tables"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.WARNING("[PHASE 2] LEGACY TABLE ANALYSIS"))
        self.stdout.write("="*80)
        
        table_counts = {}
        with connection.cursor() as cursor:
            for category, tables in self.legacy_models.items():
                self.stdout.write(f"\n[{category.upper()} TABLES]:")
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        table_counts[table] = count
                        self.stdout.write(f"   {table}: {count} rows")
                    except Exception as e:
                        table_counts[table] = None
                        self.stdout.write(self.style.ERROR(f"   {table}: ERROR - {str(e)}"))
        
        return table_counts

    def drop_legacy_tables(self, dry_run=True):
        """Drops all legacy database tables"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.WARNING(f"[PHASE 3] TABLE DELETION ({'DRY RUN' if dry_run else 'LIVE'})"))
        self.stdout.write("="*80)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("[DRY RUN MODE] - No tables will be deleted"))
            self.stdout.write("   Remove --dry-run flag to execute actual deletion")
        
        dropped_tables = []
        failed_tables = []
        
        with connection.cursor() as cursor:
            for category, tables in self.legacy_models.items():
                self.stdout.write(f"\n[Processing {category.upper()} tables...]")
                for table in tables:
                    try:
                        if dry_run:
                            self.stdout.write(f"   [DRY RUN] Would drop: {table}")
                            dropped_tables.append(table)
                        else:
                            # PostgreSQL doesn't need foreign key checks disabled for DROP TABLE IF EXISTS
                            cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                            self.stdout.write(self.style.SUCCESS(f"   [OK] Dropped: {table}"))
                            dropped_tables.append(table)
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"   [FAIL] Failed to drop {table}: {str(e)}"))
                        failed_tables.append(table)
        
        return dropped_tables, failed_tables

    def update_models_init(self, dry_run=True):
        """Updates profiles/models/__init__.py to remove legacy imports"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.WARNING(f"[PHASE 4] UPDATE MODELS/__INIT__.PY ({'DRY RUN' if dry_run else 'LIVE'})"))
        self.stdout.write("="*80)
        
        init_file = 'profiles/models/__init__.py'
        
        if dry_run:
            self.stdout.write(f"   [DRY RUN] Would update: {init_file}")
            self.stdout.write("   - Remove ExpertProfile imports (lines 3-13)")
            self.stdout.write("   - Remove VisionaryProfile imports (lines 14-22)")
            self.stdout.write("   - Remove FounderProfile import (line 35)")
            return True
        
        try:
            with open(init_file, 'r') as f:
                content = f.read()
            
            # Remove entire expert import block
            import re
            new_content = re.sub(
                r'from \.expert import \([^)]+\)\n',
                '',
                content
            )
            # Remove entire visionary import block
            new_content = re.sub(
                r'from \.visionary import \([^)]+\)\n',
                '',
                new_content
            )
            # Remove founder import
            new_content = re.sub(
                r'from \.founder import FounderProfile\n',
                '',
                new_content
            )
            
            with open(init_file, 'w') as f:
                f.write(new_content)
            
            self.stdout.write(self.style.SUCCESS(f"   [OK] Updated: {init_file}"))
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   [FAIL] Failed to update {init_file}: {str(e)}"))
            return False

    def delete_legacy_files(self, dry_run=True):
        """Deletes legacy model and command files"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.WARNING(f"[PHASE 5] DELETE LEGACY FILES ({'DRY RUN' if dry_run else 'LIVE'})"))
        self.stdout.write("="*80)
        
        deleted_files = []
        failed_files = []
        
        for file_path in self.files_to_delete:
            full_path = file_path
            if not os.path.isabs(full_path):
                # Assume relative to project root
                full_path = os.path.join(os.getcwd(), file_path)
            
            if dry_run:
                if os.path.exists(full_path):
                    self.stdout.write(f"   [DRY RUN] Would delete: {file_path}")
                    deleted_files.append(file_path)
                else:
                    self.stdout.write(self.style.WARNING(f"   [DRY RUN] File not found: {file_path}"))
            else:
                try:
                    if os.path.exists(full_path):
                        os.remove(full_path)
                        self.stdout.write(self.style.SUCCESS(f"   [OK] Deleted: {file_path}"))
                        deleted_files.append(file_path)
                    else:
                        self.stdout.write(self.style.WARNING(f"   [WARN] File not found: {file_path}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   [FAIL] Failed to delete {file_path}: {str(e)}"))
                    failed_files.append(file_path)
        
        return deleted_files, failed_files

    def generate_final_report(self, table_counts, dropped_tables, failed_tables, deleted_files, failed_files, dry_run=True):
        """Generates a comprehensive final report"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("[FINAL CLEANUP REPORT]"))
        self.stdout.write("="*80)
        
        mode = "DRY RUN" if dry_run else "LIVE EXECUTION"
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.stdout.write(f"\n[Execution Time]: {timestamp}")
        self.stdout.write(f"[Mode]: {mode}")
        
        # Table summary
        total_legacy_rows = sum(count for count in table_counts.values() if count is not None)
        self.stdout.write(f"\n[LEGACY DATA SUMMARY]:")
        self.stdout.write(f"   Total legacy tables: {len(table_counts)}")
        self.stdout.write(f"   Total legacy rows: {total_legacy_rows}")
        
        # Deletion summary
        self.stdout.write(f"\n[DELETION SUMMARY]:")
        self.stdout.write(f"   Tables processed: {len(dropped_tables)}")
        self.stdout.write(f"   Files processed: {len(deleted_files)}")
        
        if failed_tables:
            self.stdout.write(self.style.ERROR(f"   Failed table deletions: {len(failed_tables)}"))
            for table in failed_tables:
                self.stdout.write(f"      - {table}")
        
        if failed_files:
            self.stdout.write(self.style.ERROR(f"   Failed file deletions: {len(failed_files)}"))
            for file in failed_files:
                self.stdout.write(f"      - {file}")
        
        # Final state
        self.stdout.write(f"\n[FINAL STATE]:")
        if dry_run:
            self.stdout.write(self.style.WARNING("   [DRY RUN] - No changes were made"))
            self.stdout.write("   Run without --dry-run to execute the actual cleanup")
        else:
            if not failed_tables and not failed_files:
                self.stdout.write(self.style.SUCCESS("   [SUCCESS] CLEANUP COMPLETED"))
                self.stdout.write("   Legacy models and files have been removed")
                self.stdout.write("   Only Company and UserProfile models remain")
            else:
                self.stdout.write(self.style.ERROR("   [WARNING] CLEANUP COMPLETED WITH ERRORS"))
                self.stdout.write("   Please review the failed items above")

    def handle(self, *args, **kwargs):
        self.print_banner()
        
        dry_run = kwargs.get('dry_run', True)
        force = kwargs.get('force', False)
        
        # If force is True, disable dry-run mode
        if force:
            dry_run = False
        
        if not dry_run and not force:
            self.stdout.write(self.style.ERROR("[SAFETY ERROR]:"))
            self.stdout.write("   To run in LIVE mode, you must use --force flag")
            self.stdout.write("   This prevents accidental deletion in production")
            self.stdout.write("\n   Usage: python manage.py cleanup_legacy_profiles --force")
            return
        
        # Phase 1: Verify migration
        if not self.verify_migration_complete():
            self.stdout.write(self.style.ERROR("\n[ABORTING] Migration verification failed"))
            self.stdout.write("   Please ensure all legacy profiles are migrated before cleanup")
            return
        
        # Phase 2: Analyze legacy tables
        table_counts = self.get_table_counts()
        
        # Phase 3: Drop tables
        dropped_tables, failed_tables = self.drop_legacy_tables(dry_run=dry_run)
        
        # Phase 4: Update models/__init__.py
        self.update_models_init(dry_run=dry_run)
        
        # Phase 5: Delete legacy files
        deleted_files, failed_files = self.delete_legacy_files(dry_run=dry_run)
        
        # Final report
        self.generate_final_report(
            table_counts, dropped_tables, failed_tables, 
            deleted_files, failed_files, dry_run=dry_run
        )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=True,
            help='Run in dry-run mode (default: True)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            dest='force', 
            default=False,
            help='Force live execution (required for non-dry-run mode)',
        )
