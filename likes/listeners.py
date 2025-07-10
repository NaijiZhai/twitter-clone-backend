from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from cache_utils.cache_utils import CacheUtils
from cache_utils.redis_helper import RedisHelper
from likes.models import Like

@receiver(post_save, sender = Like)
def increase_likes_counter(sender, instance, created, **kwargs):
    from tweets.models import Tweet
    from django.db.models import F

    if not created:
        return

    model = instance.content_type.model_class()
    #atomic operation
    # will be like UPDATE tweet SET likes_count = likes_count + 1 WHERE id = ...
    model.objects.filter(id=instance.content_id).update(likes_count=F('likes_count')+1)
    # CacheUtils.invalidate_cache(model, instance.content_id)
    # this is not good, the cache will be deactivated all the time

    RedisHelper.increment_count(instance.target, 'likes_count')


@receiver(post_delete, sender = Like)
def decrease_likes_counter(sender, instance, **kwargs):
    from tweets.models import Tweet
    from django.db.models import F

    model = instance.content_type.model_class()
    # atomic operation
    model.objects.filter(id=instance.content_id).update(likes_count=F('likes_count') - 1)
    # CacheUtils.invalidate_cache(model, instance.content_id)

    RedisHelper.decrement_count(instance.target, 'likes_count')

