import time

from django.contrib.auth.models import User
from django.db import models
from django.db.models import ForeignKey
from datetime import datetime, timezone


# Create your models here.
class Tweet(models.Model):
    user = ForeignKey(User
                      , on_delete=models.SET_NULL,
                      null=True,
                      help_text='the one sends the tweet'
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text='the date the tweet was created')
    content = models.CharField(max_length= 255,help_text='the content of the tweet')
    # updated_at = models.DateTimeField(auto_now=True, help_text='the date the tweet was updated')

    class Meta:
        index_together = (('user', 'created_at'),)
        ordering = ('user', '-created_at',)

    @property
    def hours_to_now(self):
        return  (datetime.now(timezone.utc) - self.created_at).total_seconds() / 3600

    def __str__(self):
        return f'{self.created_at} {self.user}: {self.content}'
