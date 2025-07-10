from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from cache_utils.cache_utils import CacheUtils
from cache_utils.redis_helper import RedisHelper
from comments.models import Comment
from tweets.models import Tweet
from django.db.models import F

@receiver(post_save, sender=Comment)
def increase_comments_count(sender, instance, created, **kwargs):
    if not created:
        return
    Tweet.objects.filter(id=instance.tweet_id).update(comments_count=F('comments_count')+1)
    # CacheUtils.invalidate_cache(Tweet, instance.tweet_id)
    RedisHelper.increment_count(instance.tweet, 'comments_count')


@receiver(post_delete, sender=Comment)
def decrease_comments_count(sender, instance, **kwargs):
    Tweet.objects.filter(id=instance.tweet_id).update(comments_count=F('comments_count')-1)
    # CacheUtils.invalidate_cache(Tweet, instance.tweet_id)
    RedisHelper.decrement_count(instance.tweet, 'comments_count')