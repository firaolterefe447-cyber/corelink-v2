from django.core.management.base import BaseCommand
from accounts.models import CustomUser
from profiles.models import UserProfile, CompanyMember, ProfileHeadline
from django.db import transaction


class Command(BaseCommand):
    help = 'Fixes missing headlines for legacy Founders.'

    def handle(self, *args, **kwargs):
        legacy_founders = CustomUser.objects.filter(role='FOUNDER')
        fixed_count = 0

        self.stdout.write("Checking Founders for missing personal headlines...")

        for founder in legacy_founders:
            # We know they have a portfolio now thanks to self-healing
            if hasattr(founder, 'portfolio'):
                portfolio = founder.portfolio

                # If they don't have a headline, let's create one based on their Company!
                if not portfolio.headlines.exists():
                    member = CompanyMember.objects.filter(user=founder, role='OWNER').first()
                    headline_title = member.job_title if member and member.job_title else "Founder"

                    ProfileHeadline.objects.create(
                        profile=portfolio,
                        title=headline_title,
                        is_primary=True,
                        order=0
                    )
                    fixed_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Added Headline '{headline_title}' for {founder.full_name}"))

        self.stdout.write(self.style.SUCCESS(f"Done! Fixed headlines for {fixed_count} founders."))