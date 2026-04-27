import os
import sys

# 1. Define the absolute path to your project
PROJECT_DIR = '/home/corelink/corelink_project'

# 2. Add the project directory to sys.path so Python can find your modules
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# 3. Explicitly set the settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

# 4. Import and point to the WSGI application
from config.wsgi import application