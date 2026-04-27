# profiles/apps.py
from django.apps import AppConfig

class ProfilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'profiles' # Make sure this matches your app name

    def ready(self):
        # ⚡ THIS IS THE POWER SWITCH! It wakes up the Oracle when the server starts.
        import profiles.signals