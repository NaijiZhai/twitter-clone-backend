from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from accounts.services import UserServices


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
        unique_together = (('from_user', 'to_user'),)
        index_together = (('from_user', 'created_at'),('to_user', 'created_at'))

    def __str__(self):
        return f'{self.from_user.username} follows {self.to_user.username} starting from {self.created_at}'

    @property
    def cached_from_user(self):
        return UserServices.get_user_by_id_through_cache(user_id=self.from_user_id)

    @property
    def cached_to_user(self):
        return UserServices.get_user_by_id_through_cache(user_id=self.to_user_id)



