from notifications.signals import notify


class NotificationService:

    @classmethod
    def send_like_notification(cls, like):
        target = like.target

        # Don't notify yourself
        if target.user == like.user:
            return

        # Use a mapping for cleaner code
        verb_mapping = {
            'tweet': 'liked your tweet',
            'comment': 'liked your comment'
        }
        verb = verb_mapping.get(target._meta.model_name, None)
        # print(
        #     f"Sending notification for {target.user} to {like.user} "
        #     f"with verb {verb} and target {target}"
        # )
        if verb:
            notify.send(
                like.user,
                recipient=target.user,
                verb=verb,
                target=target
            )

    @classmethod
    def send_comment_notification(cls, comment):
        target = comment.tweet

        if target.user == comment.user:
            return

        notify.send(
                comment.user,
                recipient=target.user,
                verb='commented on your tweet',
                target=target)