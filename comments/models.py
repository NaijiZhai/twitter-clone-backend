from django.contrib.auth.models import User
from django.db import models
from django.db.models import ForeignKey

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

    def __str__(self):
        return f'at {self.updated_at} {self.user} comments {self.content} on {self.tweet}'

