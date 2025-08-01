from celery import shared_task
from notifications.signals import notify


@shared_task(queue='HighPriority')
def send_notification_async(actor_id, recipient_id, verb, target_type, target_id):
    """通用的异步通知发送"""
    from django.contrib.auth.models import User
    from django.apps import apps

    # 获取 actor 和 recipient
    actor = User.objects.get(id=actor_id)
    recipient = User.objects.get(id=recipient_id)

    # 动态获取 target model
    app_label, model_name = target_type.split('.')
    model = apps.get_model(app_label, model_name)
    target = model.objects.get(id=target_id)

    # 发送通知
    notify.send(
        actor,
        recipient=recipient,
        verb=verb,
        target=target
    )
