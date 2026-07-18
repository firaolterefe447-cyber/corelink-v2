#!/usr/bin/env python
"""
NetworkPost Table Cleanup Script
==================================
This script safely removes the NetworkPost table from the database.
Run this script on both local and production (cPanel) environments.

IMPORTANT: 
- Backup your database before running this script
- Ensure Django settings are properly configured
- Run with: python drop_networkpost_table.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.core.management import call_command


def check_table_exists():
    """Check if NetworkPost table exists in database."""
    with connection.cursor() as cursor:
        # Check database vendor and use appropriate query
        if connection.vendor == 'postgresql':
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'network_networkpost'
                );
            """)
        elif connection.vendor == 'sqlite':
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='network_networkpost';
            """)
        elif connection.vendor == 'mysql':
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'network_networkpost'
                );
            """)
        else:
            # Fallback: try to query the table directly
            try:
                cursor.execute("SELECT 1 FROM network_networkpost LIMIT 1")
                return True
            except:
                return False
        
        result = cursor.fetchone()
        return result[0] if result else False


def drop_table_sql():
    """Drop the NetworkPost table using raw SQL."""
    with connection.cursor() as cursor:
        try:
            cursor.execute("DROP TABLE IF EXISTS network_networkpost;")
            print("✓ NetworkPost table dropped successfully")
            return True
        except Exception as e:
            print(f"✗ Error dropping table: {e}")
            return False


def cleanup_migrations():
    """Clean up migration files related to NetworkPost."""
    print("\n--- Cleaning up migration files ---")
    
    # List of migration files to remove
    migration_files = [
        '0001_initial.py',
        '0002_networkpost_delete_signal_and_more.py',
        '0003_alter_networkpost_headline.py',
        '0004_alter_networkpost_headline.py',
        '0005_alter_networkpost_headline.py',
        '0006_alter_networkpost_options_alter_networkpost_author_and_more.py',
        '0007_drop_network_post.py',
        '0008_drop_networkpost.py',
    ]
    
    migrations_dir = os.path.join(os.path.dirname(__file__), 'network', 'migrations')
    
    for migration_file in migration_files:
        file_path = os.path.join(migrations_dir, migration_file)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✓ Removed: {migration_file}")
            except Exception as e:
                print(f"✗ Error removing {migration_file}: {e}")


def main():
    """Main cleanup function."""
    print("=" * 60)
    print("NetworkPost Table Cleanup Script")
    print("=" * 60)
    
    # Check if table exists
    print("\n--- Checking for NetworkPost table ---")
    if check_table_exists():
        print("✓ NetworkPost table found")
    else:
        print("✗ NetworkPost table not found (already removed)")
        return
    
    # Confirm before proceeding
    response = input("\n⚠️  WARNING: This will permanently delete the NetworkPost table and all its data.\n")
    response = input("Type 'YES' to confirm: ")
    
    if response != 'YES':
        print("❌ Cleanup cancelled")
        return
    
    # Drop the table
    print("\n--- Dropping NetworkPost table ---")
    if drop_table_sql():
        print("\n✓ Table dropped successfully")
    else:
        print("\n✗ Failed to drop table")
        return
    
    # Clean up migrations
    cleanup_migrations()
    
    # Create fresh migration file
    print("\n--- Creating fresh migration ---")
    try:
        call_command('makemigrations', 'network', '--empty')
        print("✓ Fresh migration created")
    except Exception as e:
        print(f"✗ Error creating migration: {e}")
    
    print("\n" + "=" * 60)
    print("✓ Cleanup completed successfully!")
    print("=" * 60)


if __name__ == '__main__':
    main()
