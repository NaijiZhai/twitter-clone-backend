from celery import shared_task
from notifications.signals import notify


@shared_task(queue='HighPriority')
def send_notification_async(actor_id, recipient_id, verb, target_type, target_id):
    from django.contrib.auth.models import User
    from django.apps import apps


    actor = User.objects.get(id=actor_id)
    recipient = User.objects.get(id=recipient_id)


    model = apps.get_model('tweets', 'Tweet')
    target = model.objects.get(id=target_id)


    notify.send(
        actor,
        recipient=recipient,
        verb=verb,
        target=target
    )