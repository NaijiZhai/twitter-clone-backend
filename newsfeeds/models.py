from django.db import models
from django.contrib.auth.models import User
from tweets.models import Tweet


# Create your models here.
class NewsFeed(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ('-created_at',)
        index_together = ('user', 'created_at')
        unique_together = ('user', 'tweet')

    def __str__(self):
        return f'NewsFeed with content {self.tweet} by {self.user} at {self.created_at}'

