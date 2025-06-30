from django.db.models.signals import post_save
from django.dispatch import receiver

from tweets.models import Tweet
from utils.cache_utils import CacheUtils


@receiver(post_save, sender=Tweet)
def invalidate_cache_post_save(sender, instance, created, **kwargs):
    CacheUtils.invalidate_cache(model = sender, id = instance.id)

@receiver(post_save, sender=Tweet)
def invalidate_cache_post_save_tweet(sender, instance, created, **kwargs):
    CacheUtils.invalidate_cache(model = Tweet, id = instance.user_id)