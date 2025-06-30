from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from friendships.services import FriendshipServices
from friendships.models import Friendship


@receiver(post_save, sender=Friendship)
def invalidate_cache_post_save(sender, instance, created, **kwargs):
    FriendshipServices.invalidate_following_cache(user_id=instance.from_user_id)

@receiver(pre_delete, sender=Friendship)
def invalidate_cache_pre_delete(sender, instance, **kwargs):
    FriendshipServices.invalidate_following_cache(user_id=instance.from_user_id)