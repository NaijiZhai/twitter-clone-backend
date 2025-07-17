from django.db import models
from django.contrib.auth.models import User

from cache_utils.cache_utils import CacheUtils


# Create your models here.
class Friendship(models.Model):
    from_user = models.ForeignKey(User,
                                  on_delete=models.SET_NULL,
                                  null=True,
                                  related_name='friendship_following_set')
    to_user = models.ForeignKey(User,
                                on_delete=models.SET_NULL,
                                null=True,
                                related_name='friendship_follower_set')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['from_user', 'to_user'],
                name='unique_from_to_user'
            )
        ]
        indexes = [
            models.Index(fields=['from_user', 'created_at'], name='idx_from_user_created'),
            models.Index(fields=['to_user', 'created_at'], name='idx_to_user_created'),
        ]

    def __str__(self):
        return f'{self.from_user.username} follows {self.to_user.username} starting from {self.created_at}'

    @property
    def cached_from_user(self):
        return  CacheUtils.get_object_in_cache(User, self.from_user_id)

    @property
    def cached_to_user(self):
        return CacheUtils.get_object_in_cache(User, self.to_user_id)



