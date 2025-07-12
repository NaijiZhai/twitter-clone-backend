import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'twitter.settings')

# Instantiate the Celery application with the name 'twitter'.
app = Celery('twitter')

# Load configuration from Django settings, using keys that start with 'CELERY'.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover task modules in all installed Django apps.
app.autodiscover_tasks()


# Define a simple debug task for testing purposes.
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
