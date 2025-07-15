from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

import cache_utils.cache_utils
from newsfeeds.models import NewsFeed
from newsfeeds.services import NewsFeedService


@receiver(post_save, sender = NewsFeed)
def push_newsfeed_to_cache(sender, instance, created, **kwargs):
    cache_utils.cache_utils.CacheUtils.set_object_in_cache(model=sender, obj=instance)
    if not created:
        return
    NewsFeedService.push_newsfeed_to_cache(instance)

@receiver(post_delete, sender = NewsFeed)
def invalidate_newsfeed_cache(sender, instance,**kwargs):
    cache_utils.cache_utils.CacheUtils.invalidate_cache(sender, instance.id)
