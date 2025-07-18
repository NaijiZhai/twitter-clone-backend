from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from cache_utils.cache_utils import CacheUtils
from cache_utils.redis_helper import RedisHelper
from comments.models import Comment
from tweets.models import Tweet
from django.db.models import F



# User A and User B like at the same time
# Timeline:

# T1: User A creates Like object
# T2: User B creates Like object
# T3: User A's post_save signal fires, likes_count +1
# T4: User B's post_save signal fires, likes_count +1
# T5: User A's transaction commits successfully
# T6: User B's transaction fails and rolls back for some reason

# Result: Only one Like object exists, but likes_count increased by 2

@receiver(post_save, sender=Comment)
def increase_comments_count(sender, instance, created, **kwargs):
    if not created:
        return
    #START TRANSACTION;
    #-- some operations
    #COMMIT;  -- or ROLLBACK;
    with transaction.atomic():
        Tweet.objects.filter(id=instance.tweet_id).update(comments_count=F('comments_count') + 1)

        # CacheUtils.invalidate_cache(Tweet, instance.tweet_id)
        transaction.on_commit(
            lambda: RedisHelper.refresh_count(instance.tweet, 'comments_count')
        )


@receiver(post_delete, sender=Comment)
def decrease_comments_count(sender, instance, **kwargs):
    with transaction.atomic():
        Tweet.objects.filter(id=instance.tweet_id).update(comments_count=F('comments_count') - 1)
        # CacheUtils.invalidate_cache(Tweet, instance.tweet_id)
        transaction.on_commit(
            lambda: RedisHelper.refresh_count(instance.tweet, 'comments_count')
        )