from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import ForeignKey

from accounts.services import UserServices
from likes.models import Like
from tweets.models import Tweet


# Create your models here.
class Comment(models.Model):
    user = ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tweet = ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content = models.TextField(max_length=140)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        index_together = (('tweet', 'created_at'),)

    @property
    def like_set(self):
        return Like.objects.filter(content_type=ContentType.objects.get_for_model(self.__class__),
                                   content_id=self.id).order_by('-created_at')

    def __str__(self):
        return f'at {self.updated_at} {self.user} comments {self.content} on {self.tweet}'

    @property
    def cached_user(self):
        return UserServices.get_user_by_id_through_cache(user_id=self.user_id)

