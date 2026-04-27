from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # We import here to prevent Django "AppRegistryNotReady" crash on startup
        from .models import CustomUser
        from watson import search as watson

        # --- THE DEEP SEARCH ADAPTER ---
        class UserDeepSearchAdapter(watson.SearchAdapter):

            def get_title(self, obj):
                # The primary name returned in search
                return obj.full_name

            def get_description(self, obj):
                # This is the "Brain". We gather all related text into one invisible block.
                text_chunks = [obj.full_name, obj.current_location or "", obj.get_role_display()]

                # 1. If VISIONARY: Grab their Headline, Bio, and Interest
                if obj.role == 'VISIONARY' and hasattr(obj, 'visionary_profile'):
                    vp = obj.visionary_profile
                    text_chunks.extend([
                        vp.headline or "",
                        vp.bio_narrative or "",
                        vp.field_of_interest or "",
                        vp.right_now or ""
                    ])

                # 2. If EXPERT: Grab Bio, Headlines, and Skills
                elif obj.role == 'EXPERT' and hasattr(obj, 'expert_profile'):
                    ep = obj.expert_profile
                    text_chunks.extend([ep.bio_narrative or "", ep.right_now or ""])

                    # Dig deeper: Grab their multiple headlines and skills!
                    for hl in ep.headlines.all():
                        text_chunks.append(hl.title)
                    for skill in ep.skills.all():
                        text_chunks.append(skill.name)

                # 3. If FOUNDER: Grab their LIVE Company Data (ignoring the temporary fields)
                elif obj.role == 'FOUNDER':
                    if hasattr(obj, 'founder_profile'):
                        text_chunks.append(obj.founder_profile.right_now or "")

                    # Dig deeper: Go into the CompanyMember table and grab the real company!
                    for membership in obj.company_memberships.filter(is_active=True):
                        company = membership.company
                        text_chunks.extend([
                            company.name,
                            company.sector,
                            company.mission_stmt,
                            membership.job_title
                        ])

                # Clean up empty strings and join into one massive search paragraph
                return " ".join([str(t) for t in text_chunks if t])

        # Register the User model with our new Super-Brain adapter
        watson.register(CustomUser, UserDeepSearchAdapter)