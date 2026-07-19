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

                # Use unified UserProfile for all roles
                if hasattr(obj, 'portfolio'):
                    profile = obj.portfolio
                    text_chunks.extend([
                        profile.bio_narrative or "",
                        profile.field_of_interest or "",
                        profile.location or "",
                        profile.institution or ""
                    ])

                    # Grab headlines
                    for hl in profile.headlines.all():
                        text_chunks.append(hl.title)

                    # Grab skills
                    for skill in profile.skills.all():
                        text_chunks.append(skill.name)

                    # Grab work experience
                    for exp in profile.experiences.all():
                        text_chunks.extend([
                            exp.company_name or "",
                            exp.role_title or "",
                            exp.description or ""
                        ])

                    # Grab projects
                    for project in profile.projects.all():
                        text_chunks.extend([
                            project.title or "",
                            project.main_description or ""
                        ])

                # For FOUNDER: Also grab company data
                if obj.role == 'FOUNDER':
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