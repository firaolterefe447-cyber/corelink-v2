from django.core.management.base import BaseCommand
from accounts.models import Country, City
from accounts.forms import UnifiedOnboardingForm


class Command(BaseCommand):
    help = 'Test city loading in the registration form'

    def handle(self, *args, **options):
        self.stdout.write('🧪 Testing city loading...')
        
        # Test 1: Check if cities are loaded in form by default
        form = UnifiedOnboardingForm()
        city_queryset = form.fields['city'].queryset
        self.stdout.write(f'📊 Default city queryset count: {city_queryset.count()}')
        
        if city_queryset.count() > 0:
            self.stdout.write('✅ Cities are loaded by default')
            for city in city_queryset[:5]:
                self.stdout.write(f'   - {city.name}')
        else:
            self.stdout.write('❌ No cities loaded by default')
        
        # Test 2: Test with a specific country
        first_country = Country.objects.filter(is_verified=True).first()
        if first_country:
            form_with_country = UnifiedOnboardingForm(data={'country': str(first_country.id)})
            city_queryset_filtered = form_with_country.fields['city'].queryset
            self.stdout.write(f'\n📊 Cities for {first_country.name}: {city_queryset_filtered.count()}')
            
            if city_queryset_filtered.count() > 0:
                self.stdout.write('✅ Cities are filtered by country')
                for city in city_queryset_filtered[:5]:
                    self.stdout.write(f'   - {city.name}')
            else:
                self.stdout.write('❌ No cities found for this country')
        
        # Test 3: Direct database check
        total_cities = City.objects.filter(is_verified=True).count()
        self.stdout.write(f'\n📊 Total verified cities in DB: {total_cities}')
        
        if total_cities == 0:
            self.stdout.write('❌ No verified cities in database')
        else:
            self.stdout.write('✅ Verified cities exist in database')
