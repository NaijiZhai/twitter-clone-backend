from django.db.models.signals import post_save
from django.dispatch import receiver

import cache_utils.redis_helper
from tweets.models import Tweet
from cache_utils.cache_utils import CacheUtils
from tweets.services import TweetService


@receiver(post_save, sender=Tweet)
def invalidate_cache_post_save(sender, instance, created, **kwargs):
    CacheUtils.invalidate_cache(model = sender, id = instance.id)

@receiver(post_save, sender=Tweet)
def invalidate_cache_post_save_tweet(sender, instance, created, **kwargs):
    CacheUtils.invalidate_cache(model = Tweet, id = instance.user_id)

@receiver(post_save, sender=Tweet)
def push_tweet_to_redis(sender, instance, created, **kwargs):
    if not created:
        return
    TweetService.push_tweets_to_cache(instance)