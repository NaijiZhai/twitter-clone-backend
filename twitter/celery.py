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
# @app.task(bind=True, queue='Twitte_Queue.fifo')
# def debug_task(self):
#     import  time
#     print(f'Before: {self.request!r}')
#     time.sleep(10)
#     print(f'Request: {self.request!r}')
