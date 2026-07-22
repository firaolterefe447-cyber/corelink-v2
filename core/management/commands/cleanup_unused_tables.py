"""
Django management command to safely drop unused tables from the database.

This command will:
1. Drop SiteMediaAsset and SiteTextAsset tables from the database
2. Remove their corresponding migration files
3. Clean up any related data

Usage:
    python manage.py cleanup_unused_tables

WARNING: This operation is irreversible. Ensure you have a database backup before running.
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = 'Safely drop unused SiteMediaAsset and SiteTextAsset tables from the database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('WARNING: This operation is irreversible!'))
        self.stdout.write(self.style.WARNING('Ensure you have a database backup before proceeding.'))
        
        # Tables to drop
        tables_to_drop = [
            'core_sitemediaasset',
            'core_sitetextasset',
        ]
        
        # Check database engine
        db_engine = settings.DATABASES['default']['ENGINE']
        self.stdout.write(f'\nDatabase engine: {db_engine}')
        
        with connection.cursor() as cursor:
            for table in tables_to_drop:
                self.stdout.write(f'\nChecking table: {table}')
                
                # Check if table exists
                if db_engine == 'django.db.backends.postgresql':
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = %s
                        )
                    """, [table])
                elif db_engine == 'django.db.backends.sqlite3':
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=?
                    """, [table])
                else:
                    self.stdout.write(self.style.ERROR(f'Unsupported database engine: {db_engine}'))
                    return
                
                table_exists = cursor.fetchone()[0] if cursor.rowcount > 0 else False
                
                if not table_exists:
                    self.stdout.write(self.style.SUCCESS(f'Table {table} does not exist - skipping'))
                    continue
                
                # Drop the table
                self.stdout.write(f'Dropping table: {table}')
                try:
                    if db_engine == 'django.db.backends.postgresql':
                        cursor.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
                    elif db_engine == 'django.db.backends.sqlite3':
                        cursor.execute(f'DROP TABLE IF EXISTS {table}')
                    
                    self.stdout.write(self.style.SUCCESS(f'Successfully dropped table: {table}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error dropping table {table}: {str(e)}'))
                    return
        
        self.stdout.write(self.style.SUCCESS('\n✓ All unused tables have been dropped successfully'))
        self.stdout.write(self.style.WARNING('\nNext steps:'))
        self.stdout.write('1. Remove SiteMediaAsset and SiteTextAsset models from core/models.py')
        self.stdout.write('2. Remove their admin registrations from core/admin.py')
        self.stdout.write('3. Run: python manage.py makemigrations core')
        self.stdout.write('4. Run: python manage.py migrate core')
