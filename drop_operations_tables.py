#!/usr/bin/env python
"""
Database Cleanup Script: Drop Operations App Tables
This script removes all tables associated with the operations app from the database.
Run this after removing the operations app from INSTALLED_APPS and deleting the app directory.
"""

import os
import sys
import django

# Setup Django environment
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from django.conf import settings

def drop_operations_tables():
    """
    Drops all tables related to the operations app.
    Handles both SQLite and PostgreSQL databases.
    """
    tables_to_drop = [
        'operations_achievementclaim',
        'operations_familyunit', 
        'operations_familymembership',
        'operations_auditlog'
    ]
    
    with connection.cursor() as cursor:
        db_backend = settings.DATABASES['default']['ENGINE']
        
        print(f"Database Backend: {db_backend}")
        print(f"Tables to drop: {tables_to_drop}")
        print("-" * 50)
        
        if 'postgresql' in db_backend:
            # PostgreSQL: Handle foreign key constraints and drop tables
            print("Using PostgreSQL cleanup...")
            
            # Disable foreign key constraint checks temporarily
            cursor.execute("SET CONSTRAINTS ALL DEFERRED")
            
            for table in tables_to_drop:
                try:
                    # Drop table if exists with CASCADE to handle dependencies
                    cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                    print(f"✓ Dropped table: {table}")
                except Exception as e:
                    print(f"✗ Error dropping {table}: {e}")
            
            # Re-enable constraints
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            
        elif 'sqlite' in db_backend:
            # SQLite: Drop tables directly
            print("Using SQLite cleanup...")
            
            for table in tables_to_drop:
                try:
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    print(f"✓ Dropped table: {table}")
                except Exception as e:
                    print(f"✗ Error dropping {table}: {e}")
        else:
            print(f"Unsupported database backend: {db_backend}")
            return False
    
    # Commit the transaction
    connection.commit()
    print("-" * 50)
    print("Database cleanup completed successfully!")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("Operations App Table Cleanup Script")
    print("=" * 50)
    print()
    
    # Safety confirmation
    response = input("This will permanently delete all operations app tables. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Operation cancelled.")
        sys.exit(0)
    
    success = drop_operations_tables()
    
    if success:
        print("\nNext steps:")
        print("1. Run: python manage.py makemigrations")
        print("2. Run: python manage.py migrate")
        print("3. Test your application to ensure everything works")
    else:
        print("\nCleanup failed. Please check the errors above.")
        sys.exit(1)
