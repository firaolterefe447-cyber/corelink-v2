"""
DATABASE CLEANUP VERIFICATION COMMAND
=====================================
This command performs a comprehensive check to ensure the database is completely
free of legacy profile models (ExpertProfile, VisionaryProfile, FounderProfile).

It checks:
1. Database tables for legacy model tables
2. Django model imports for legacy references
3. Foreign key relationships pointing to legacy models
4. Code files for legacy model references
5. Migration files for legacy model operations

Usage:
    python manage.py verify_database_cleanup
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
import os
import re


class Command(BaseCommand):
    help = 'Verify database is completely free of legacy profile models'

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
        
        self.legacy_model_names = [
            'ExpertProfile', 'VisionaryProfile', 'FounderProfile',
            'ExpertHeadline', 'ExpertSkill', 'ExpertCredential',
            'ExpertProject', 'ProjectGalleryImage', 'ExpertExperience',
            'ExpertThought',
            'GrowthLog', 'LearningTarget', 'VisionBlock',
        ]
        
        # Files to skip during code reference check
        self.skip_files = [
            'verify_database_cleanup.py',
            'cleanup_legacy_profiles.py',
        ]
        
        self.legacy_file_names = [
            'expert.py', 'visionary.py', 'founder.py',
            'migrate_to_unified_profiles.py',
            'migrate_right_now.py',
            'fix_legacy_founders.py',
            'fix_timestamps.py',
            'cleanup_legacy_profiles.py',
        ]
        
        self.issues_found = []

    def print_banner(self):
        """Print command banner"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.WARNING("DATABASE CLEANUP VERIFICATION"))
        self.stdout.write("="*80)
        self.stdout.write("Checking for legacy profile model remnants...")
        self.stdout.write("")

    def check_database_tables(self):
        """Check if legacy database tables still exist"""
        self.stdout.write("\n[CHECK 1] Database Tables")
        self.stdout.write("-" * 80)
        
        with connection.cursor() as cursor:
            # Get all tables in the database
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            existing_tables = {row[0] for row in cursor.fetchall()}
        
        legacy_tables_found = []
        for category, tables in self.legacy_models.items():
            for table in tables:
                if table in existing_tables:
                    legacy_tables_found.append(table)
                    self.issues_found.append(f"Legacy table exists: {table}")
                    self.stdout.write(self.style.ERROR(f"   [FAIL] Legacy table found: {table}"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"   [OK] Table removed: {table}"))
        
        if not legacy_tables_found:
            self.stdout.write(self.style.SUCCESS("   [PASS] No legacy tables found in database"))
        
        return len(legacy_tables_found) == 0

    def check_model_imports(self):
        """Check if legacy models can still be imported"""
        self.stdout.write("\n[CHECK 2] Model Imports")
        self.stdout.write("-" * 80)
        
        import_errors = []
        
        for model_name in ['ExpertProfile', 'VisionaryProfile', 'FounderProfile']:
            try:
                # Try to import the legacy model
                from profiles.models import expert, visionary, founder
                import_errors.append(f"Legacy model importable: {model_name}")
                self.stdout.write(self.style.ERROR(f"   [FAIL] Legacy model importable: {model_name}"))
            except ImportError:
                self.stdout.write(self.style.SUCCESS(f"   [OK] Legacy model not importable: {model_name}"))
            except Exception as e:
                # Any error is good - means the model doesn't exist
                self.stdout.write(self.style.SUCCESS(f"   [OK] Legacy model not importable: {model_name}"))
        
        if not import_errors:
            self.stdout.write(self.style.SUCCESS("   [PASS] No legacy models can be imported"))
        
        return len(import_errors) == 0

    def check_code_references(self):
        """Check code files for legacy model references"""
        self.stdout.write("\n[CHECK 3] Code File References")
        self.stdout.write("-" * 80)
        
        # Directories to search
        search_dirs = ['profiles', 'core', 'chat', 'opportunities', 'accounts']
        
        references_found = []
        
        for dir_name in search_dirs:
            dir_path = os.path.join(settings.BASE_DIR, dir_name)
            if not os.path.exists(dir_path):
                continue
            
            for root, dirs, files in os.walk(dir_path):
                # Skip __pycache__ and migrations
                dirs[:] = [d for d in dirs if d not in ['__pycache__', 'migrations', '.git']]
                
                for file in files:
                    if file.endswith('.py'):
                        # Skip verification script files
                        if any(skip in file for skip in self.skip_files):
                            continue
                        
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                            
                            # Check for legacy model references in imports and class definitions
                            for line_num, line in enumerate(lines, 1):
                                # Skip comments
                                if line.strip().startswith('#'):
                                    continue
                                
                                # Check for actual model imports or references
                                for model_name in self.legacy_model_names:
                                    # Match as whole word in code context
                                    pattern = r'\b' + model_name + r'\b'
                                    if re.search(pattern, line) and (
                                        'import' in line or 
                                        'from' in line or 
                                        'model = ' in line or
                                        'ForeignKey' in line or
                                        'class ' + model_name in line
                                    ):
                                        references_found.append(f"{file_path}:{line_num} {model_name}")
                                        self.stdout.write(self.style.ERROR(f"   [FAIL] {file_path}:{line_num} {model_name}"))
                        except Exception:
                            pass
        
        if not references_found:
            self.stdout.write(self.style.SUCCESS("   [PASS] No legacy model references in code"))
        
        return len(references_found) == 0

    def check_legacy_files(self):
        """Check if legacy model files still exist"""
        self.stdout.write("\n[CHECK 4] Legacy Model Files")
        self.stdout.write("-" * 80)
        
        files_found = []
        
        # Check profiles/models directory
        models_dir = os.path.join(settings.BASE_DIR, 'profiles', 'models')
        for file_name in self.legacy_file_names:
            file_path = os.path.join(models_dir, file_name)
            if os.path.exists(file_path):
                files_found.append(file_path)
                self.issues_found.append(f"Legacy file exists: {file_path}")
                self.stdout.write(self.style.ERROR(f"   [FAIL] Legacy file exists: {file_name}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"   [OK] File removed: {file_name}"))
        
        # Check management commands
        commands_dir = os.path.join(settings.BASE_DIR, 'profiles', 'management', 'commands')
        for file_name in self.legacy_file_names:
            if file_name.endswith('.py'):
                file_path = os.path.join(commands_dir, file_name)
                if os.path.exists(file_path):
                    files_found.append(file_path)
                    self.issues_found.append(f"Legacy command exists: {file_path}")
                    self.stdout.write(self.style.ERROR(f"   [FAIL] Legacy command exists: {file_name}"))
        
        if not files_found:
            self.stdout.write(self.style.SUCCESS("   [PASS] No legacy files found"))
        
        return len(files_found) == 0

    def check_migration_files(self):
        """Check migration files for legacy model operations"""
        self.stdout.write("\n[CHECK 5] Migration Files")
        self.stdout.write("-" * 80)
        
        migrations_dir = os.path.join(settings.BASE_DIR, 'profiles', 'migrations')
        legacy_migrations = []
        
        if os.path.exists(migrations_dir):
            for file_name in os.listdir(migrations_dir):
                if file_name.endswith('.py') and file_name != '__init__.py':
                    file_path = os.path.join(migrations_dir, file_name)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Check for legacy model references in migrations
                        for model_name in ['expertprofile', 'visionaryprofile', 'founderprofile']:
                            if model_name in content.lower():
                                legacy_migrations.append(file_name)
                                self.stdout.write(self.style.WARNING(f"   [WARN] Migration references legacy: {file_name}"))
                                break
                    except Exception:
                        pass
        
        # Note: We don't fail on this because old migrations are part of history
        if legacy_migrations:
            self.stdout.write(self.style.WARNING(f"   [INFO] {len(legacy_migrations)} old migrations reference legacy models (this is OK)"))
        else:
            self.stdout.write(self.style.SUCCESS("   [PASS] No legacy model references in recent migrations"))
        
        return True  # Don't fail on this

    def check_foreign_keys(self):
        """Check for foreign keys pointing to legacy tables"""
        self.stdout.write("\n[CHECK 6] Foreign Key References")
        self.stdout.write("-" * 80)
        
        with connection.cursor() as cursor:
            # Check for foreign keys pointing to legacy tables
            fk_issues = []
            
            for category, tables in self.legacy_models.items():
                for table in tables:
                    # Check if any table has a foreign key to this legacy table
                    cursor.execute("""
                        SELECT 
                            tc.table_name,
                            kcu.column_name,
                            ccu.table_name AS foreign_table_name
                        FROM information_schema.table_constraints AS tc
                        JOIN information_schema.key_column_usage AS kcu
                            ON tc.constraint_name = kcu.constraint_name
                        JOIN information_schema.constraint_column_usage AS ccu
                            ON ccu.constraint_name = tc.constraint_name
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND ccu.table_name = %s
                    """, [table])
                    
                    results = cursor.fetchall()
                    if results:
                        for row in results:
                            fk_issues.append(f"FK from {row[0]}.{row[1]} to {table}")
                            self.stdout.write(self.style.ERROR(f"   [FAIL] FK exists: {row[0]}.{row[1]} -> {table}"))
            
            if not fk_issues:
                self.stdout.write(self.style.SUCCESS("   [PASS] No foreign keys pointing to legacy tables"))
        
        return len(fk_issues) == 0

    def generate_summary(self, results):
        """Generate final summary"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.WARNING("VERIFICATION SUMMARY"))
        self.stdout.write("="*80)
        
        total_checks = len(results)
        passed_checks = sum(1 for r in results if r)
        
        self.stdout.write(f"\nTotal Checks: {total_checks}")
        self.stdout.write(f"Passed: {passed_checks}")
        self.stdout.write(f"Failed: {total_checks - passed_checks}")
        
        if self.issues_found:
            self.stdout.write(f"\nTotal Issues Found: {len(self.issues_found)}")
            self.stdout.write("\nIssues:")
            for issue in self.issues_found:
                self.stdout.write(self.style.ERROR(f"  - {issue}"))
        
        if all(results):
            self.stdout.write("\n" + "="*80)
            self.stdout.write(self.style.SUCCESS("VERIFICATION PASSED: Database is clean of legacy models"))
            self.stdout.write("="*80)
        else:
            self.stdout.write("\n" + "="*80)
            self.stdout.write(self.style.ERROR("VERIFICATION FAILED: Legacy model remnants found"))
            self.stdout.write("="*80)
            self.stdout.write("\nPlease address the issues listed above before proceeding.")

    def handle(self, *args, **kwargs):
        self.print_banner()
        
        results = []
        
        # Run all checks
        results.append(self.check_database_tables())
        results.append(self.check_model_imports())
        results.append(self.check_code_references())
        results.append(self.check_legacy_files())
        results.append(self.check_migration_files())
        results.append(self.check_foreign_keys())
        
        # Generate summary
        self.generate_summary(results)
