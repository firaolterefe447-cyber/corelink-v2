from django.core.management.base import BaseCommand
from accounts.models import Country, City, Institution


class Command(BaseCommand):
    help = 'Check verification status of countries, cities, and institutions'

    def handle(self, *args, **options):
        self.stdout.write('📊 Checking location verification status...')
        
        # Countries
        total_countries = Country.objects.count()
        verified_countries = Country.objects.filter(is_verified=True).count()
        unverified_countries = total_countries - verified_countries
        
        self.stdout.write(f'\n🌍 Countries:')
        self.stdout.write(f'   Total: {total_countries}')
        self.stdout.write(f'   Verified: {verified_countries}')
        self.stdout.write(f'   Unverified: {unverified_countries}')
        
        if unverified_countries > 0:
            self.stdout.write('   Unverified countries:')
            for country in Country.objects.filter(is_verified=False)[:5]:
                self.stdout.write(f'     - {country.name}')
        
        # Cities
        total_cities = City.objects.count()
        verified_cities = City.objects.filter(is_verified=True).count()
        unverified_cities = total_cities - verified_cities
        
        self.stdout.write(f'\n🏙️  Cities:')
        self.stdout.write(f'   Total: {total_cities}')
        self.stdout.write(f'   Verified: {verified_cities}')
        self.stdout.write(f'   Unverified: {unverified_cities}')
        
        if unverified_cities > 0:
            self.stdout.write('   Unverified cities:')
            for city in City.objects.filter(is_verified=False)[:5]:
                self.stdout.write(f'     - {city.name} ({city.Country.name if city.Country else "No Country"})')
        
        # Institutions
        total_institutions = Institution.objects.count()
        verified_institutions = Institution.objects.filter(is_verified=True).count()
        unverified_institutions = total_institutions - verified_institutions
        
        self.stdout.write(f'\n🎓 Institutions:')
        self.stdout.write(f'   Total: {total_institutions}')
        self.stdout.write(f'   Verified: {verified_institutions}')
        self.stdout.write(f'   Unverified: {unverified_institutions}')
        
        if unverified_institutions > 0:
            self.stdout.write('   Unverified institutions:')
            for inst in Institution.objects.filter(is_verified=False)[:5]:
                self.stdout.write(f'     - {inst.name}')
        
        # Summary
        total_unverified = unverified_countries + unverified_cities + unverified_institutions
        if total_unverified == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ All locations are verified and should be visible on registration!'))
        else:
            self.stdout.write(self.style.WARNING(f'\n⚠️  {total_unverified} total locations are unverified and will NOT be visible on registration.'))
            self.stdout.write(self.style.WARNING('Run: python manage.py fix_location_verification'))
