from django.db import models
from django.contrib.auth.models import User
from tweets.models import Tweet
from cache_utils.cache_utils import CacheUtils


# Create your models here.
class NewsFeed(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)
    insert_tag = models.CharField(max_length=36, null=False, db_index=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['user', 'tweet'], name='unique_user_tweet')
        ]

    def __str__(self):
        return f'NewsFeed with content {self.tweet} by {self.user} at {self.created_at}'

    @property
    def cached_tweet(self):
        return CacheUtils.get_object_in_cache(model= Tweet, id = self.tweet_id)

