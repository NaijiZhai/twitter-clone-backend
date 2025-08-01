from notifications.signals import notify
from notification.tasks import send_notification_async

class NotificationService:

    @classmethod
    def send_like_notification(cls, like):
        target = like.target

        # Don't notify yourself
        if target.user_id == like.user_id:
            return

        # Use a mapping for cleaner code
        verb_mapping = {
            'tweet': 'liked your tweet',
            'comment': 'liked your comment'
        }
        verb = verb_mapping.get(target._meta.model_name, None)

        if verb:
            # 异步发送！
            send_notification_async.delay(
                actor_id=like.user_id,
                recipient_id=target.user_id,
                verb=verb,
                target_type=f'{target._meta.app_label}.{target._meta.model_name}',
                target_id=target.id
            )

    @classmethod
    def send_comment_notification(cls, comment):
        target = comment.tweet

        if target.user_id == comment.user_id:
            return

        send_notification_async.delay(
            actor_id=comment.user_id,
            recipient_id=target.user_id,
            verb='commented on your tweet',
            target_type='tweets.Tweet',
            target_id=target.id
        )