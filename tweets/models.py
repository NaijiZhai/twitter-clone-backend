from datetime import datetime, timezone

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import ForeignKey

from accounts.services import UserServices
from likes.models import Like
from tweets.constants import TweetPhotoStatus, TWEET_PHOTO_STATUS_CHOICES
from utils.cache_utils import CacheUtils


# Create your models here.
class Tweet(models.Model):
    user = ForeignKey(User
                      , on_delete=models.SET_NULL,
                      null=True,
                      help_text='the one sends the tweet'
                      )
    created_at = models.DateTimeField(auto_now_add=True, help_text='the date the tweet was created')
    content = models.CharField(max_length=255, help_text='the content of the tweet')

    # updated_at = models.DateTimeField(auto_now=True, help_text='the date the tweet was updated')

    class Meta:
        index_together = (('user', 'created_at'),)
        ordering = ('user', '-created_at',)

    @property
    def hours_to_now(self):
        return (datetime.now(timezone.utc) - self.created_at).total_seconds() / 3600

    @property
    def like_set(self):
        return Like.objects.filter(content_type=ContentType.objects.get_for_model(self.__class__),
                                   content_id=self.id).order_by('-created_at')

    def __str__(self):
        return f'{self.created_at} {self.user}: {self.content}'

    @property
    def cached_user(self):
        return CacheUtils.get_object_in_cache(User, self.user_id)


class TweetPhoto(models.Model):
    tweet = ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)
    user = ForeignKey(User, on_delete=models.SET_NULL, null=True)


    file = models.FileField()
    order = models.IntegerField(default=0)

    status = models.IntegerField(choices=TWEET_PHOTO_STATUS_CHOICES, default= TweetPhotoStatus.PENDING)

    has_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = [
            ('tweet', 'order'),# most common pattern
            ('user', 'created_at'),# querying all photos by a user in chronological order
            ('tweet', 'status', 'has_deleted'),  # combined filter for tweet photos
            ('status', 'created_at'),  # for admin dashboard queries
            ('has_deleted', 'created_at'), # for recycle
        ]

    def __str__(self):
        return f'{self.tweet} {self.user} {self.status}'