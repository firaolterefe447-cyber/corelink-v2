# opportunities/apps.py

from django.apps import AppConfig

class OpportunitiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'opportunities'

    def ready(self):
        # 1. CONNECT THE SIGNALS
        # import opportunities.signals (Uncomment when you add signals)

        # 2. CONNECT THE SEARCH ENGINE (Watson)
        try:
            from watson import search as watson
            from .models import JobPost

            # Register the model directly (Safe for migrations)
            watson.register(
                JobPost,
                fields=("title", "description", "location", "compensation_text")
            )
        except ImportError:
            pass