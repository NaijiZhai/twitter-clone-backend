from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

import cache_utils.redis_helper
from tweets.models import Tweet
from cache_utils.cache_utils import CacheUtils
from tweets.services import TweetService


@receiver(post_save, sender=Tweet)
def invalidate_cache_post_save(sender, instance, created, **kwargs):
    CacheUtils.set_object_in_cache(model=Tweet, obj=instance)

@receiver(post_save, sender=Tweet)
def invalidate_cache_post_save_tweet(sender, instance, created, **kwargs):
    CacheUtils.set_object_in_cache(model=Tweet, obj=instance)


@receiver(post_save, sender=Tweet)
def push_tweet_to_redis(sender, instance, created, **kwargs):
    if not created:
        return
    TweetService.push_tweets_to_cache(instance)

@receiver(post_delete, sender=Tweet)
def invalidate_cache_post_delete(sender, instance, **kwargs):
    TweetService.delete_cache(instance)
    CacheUtils.invalidate_cache(Tweet, instance.id)