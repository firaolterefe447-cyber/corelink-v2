from django.core.management.base import BaseCommand
from accounts.models import Country, City, Institution


class Command(BaseCommand):
    help = 'Fix verification status for countries, cities, and institutions to make them visible in registration'

    def handle(self, *args, **options):
        self.stdout.write('🔧 Fixing location verification status...')
        
        # Update all countries to be verified
        country_count = Country.objects.filter(is_verified=False).update(is_verified=True)
        self.stdout.write(self.style.SUCCESS(f'✅ Updated {country_count} countries to verified=True'))
        
        # Update all cities to be verified
        city_count = City.objects.filter(is_verified=False).update(is_verified=True)
        self.stdout.write(self.style.SUCCESS(f'✅ Updated {city_count} cities to verified=True'))
        
        # Update all institutions to be verified
        inst_count = Institution.objects.filter(is_verified=False).update(is_verified=True)
        self.stdout.write(self.style.SUCCESS(f'✅ Updated {inst_count} institutions to verified=True'))
        
        # Show current counts
        total_countries = Country.objects.count()
        verified_countries = Country.objects.filter(is_verified=True).count()
        total_cities = City.objects.count()
        verified_cities = City.objects.filter(is_verified=True).count()
        total_institutions = Institution.objects.count()
        verified_institutions = Institution.objects.filter(is_verified=True).count()
        
        self.stdout.write('\n📊 Current Status:')
        self.stdout.write(f'   Countries: {verified_countries}/{total_countries} verified')
        self.stdout.write(f'   Cities: {verified_cities}/{total_cities} verified')
        self.stdout.write(f'   Institutions: {verified_institutions}/{total_institutions} verified')
        
        self.stdout.write(self.style.SUCCESS('\n🎉 All locations are now verified and visible on the registration page!'))
