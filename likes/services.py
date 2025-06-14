from django.contrib.contenttypes.models import ContentType

from likes.models import Like


class LikeService(object):

    @classmethod
    def has_user_liked(cls, user, post):
        if user.is_anonymous:
            return False
        return Like.objects.filter(user=user, content_type=ContentType.objects.get_for_model(post),
                                   content_id=post.id).exists()
