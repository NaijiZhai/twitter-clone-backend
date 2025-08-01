import uuid
from datetime import datetime, timedelta
from django.utils import timezone

from celery import shared_task
from celery.utils.log import logger
from django.contrib.auth.models import User

import cache_utils
from cache_utils.redis_client import RedisClient
from friendships.services import FriendshipServices
from newsfeeds.models import NewsFeed
from celery import shared_task

from friendships.services import FriendshipServices
from newsfeeds.models import NewsFeed
from tweets.models import Tweet
from twitter import settings

FANOUT_BATCH_SIZE = 1000 if not settings.TESTING else 3


@shared_task(queue='HighPriority', time_limit=360)
def fanout_newsfeeds_main_task(tweet_id, created_at, tweet_user_id):
    created_at = datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at
    NewsFeed.objects.create(
        user_id=tweet_user_id,
        tweet_id=tweet_id,
        created_at=created_at,
    )

    follower_ids = FriendshipServices.get_followers(tweet_user_id)
    index = 0
    while index < len(follower_ids):
        batch_ids = follower_ids[index: index + FANOUT_BATCH_SIZE]
        try:
            fanout_newsfeeds_batch_task.delay(tweet_id, created_at.isoformat(), batch_ids)
        except Exception as e:
            logger.error(f'Error dispatching fanout batch: {e}, batch_ids: {batch_ids}')
        index += FANOUT_BATCH_SIZE

    return '{} newsfeeds going to fanout, {} batches created.'.format(
        len(follower_ids),
        (len(follower_ids) + FANOUT_BATCH_SIZE - 1) // FANOUT_BATCH_SIZE,
    )


@shared_task(queue='Standard', time_limit=360)
def fanout_newsfeeds_batch_task(tweet_id, created_at, batch_ids):
    created_at = datetime.fromisoformat(created_at) if isinstance(created_at, str) else created_at
    from newsfeeds.services import NewsFeedService
    tag = str(uuid.uuid4())
    newsfeeds = [
        NewsFeed(tweet_id=tweet_id, created_at=created_at, user_id=user_id, insert_tag=tag) for user_id in batch_ids
    ]
    NewsFeed.objects.bulk_create(newsfeeds)
    newsfeeds = NewsFeed.objects.filter(insert_tag=tag)
    for newsfeed in newsfeeds:
        NewsFeedService.push_newsfeed_to_cache(newsfeed)

    return "{} newsfeeds created".format(len(newsfeeds))


@shared_task(queue='LowPriority')
def sync_newsfeed_cache_task(user_id):
    """
    同步用户的newsfeed缓存 - 优化版
    """
    try:
        following_ids = FriendshipServices.get_following_id_set(user_id)
        following_ids.add(user_id)

        # 获取最新的推文
        recent_tweets = Tweet.objects.filter(
            user_id__in=following_ids,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).select_related('user').order_by('-created_at', '-id')[:100]

        if not recent_tweets:
            return f"No recent tweets for user {user_id}"

        # 🔥 批量查询：一次性获取所有可能存在的NewsFeed记录
        tweet_ids = [tweet.id for tweet in recent_tweets]
        existing_newsfeeds = NewsFeed.objects.filter(
            user_id=user_id,
            tweet_id__in=tweet_ids
        ).select_related('tweet', 'tweet__user')

        # 🔥 创建字典映射以便快速查找
        existing_newsfeed_map = {nf.tweet_id: nf for nf in existing_newsfeeds}

        # 更新缓存
        from cache_utils.cache_constants import NEWSFEED_USER_PATTERN
        from cache_utils.redis_helper import RedisHelper

        key = NEWSFEED_USER_PATTERN.format(user_id=user_id)
        RedisHelper.invalidate_cache(key)

        from newsfeeds.services import NewsFeedService

        # 🔥 现在只需要字典查找，没有数据库查询
        for tweet in recent_tweets:
            existing_newsfeed = existing_newsfeed_map.get(tweet.id)

            if existing_newsfeed:
                # 使用真实的NewsFeed对象
                NewsFeedService.push_newsfeed_to_cache(existing_newsfeed)
            else:
                # 创建伪NewsFeed对象用于缓存（pull模式）
                pseudo_newsfeed = type('NewsFeed', (), {
                    'id': f"sync_{tweet.id}",
                    'tweet': tweet,
                    'tweet_id': tweet.id,
                    'user_id': user_id,
                    'created_at': tweet.created_at,
                })()
                NewsFeedService.push_newsfeed_to_cache(pseudo_newsfeed)

        return f"Synced cache for user {user_id} with {len(recent_tweets)} tweets"

    except Exception as e:
        logger.error(f"Error syncing cache for user {user_id}: {str(e)}")
        return f"Error syncing cache for user {user_id}: {str(e)}"


@shared_task(queue='LowPriority', time_limit=600)
def bulk_sync_newsfeed_caches():
    """
    daily update cache for active users
    """
    try:
        # get active users
        recent_time = datetime.now() - timedelta(hours=24)
        active_users = User.objects.filter(
            last_login__gte=recent_time
        ).values_list('id', flat=True)

        synced_count = 0
        for user_id in active_users:
            try:
                sync_newsfeed_cache_task.delay(user_id)
                synced_count += 1
            except Exception as e:
                logger.error(f"Error triggering sync for user {user_id}: {e}")

        return f"Triggered cache sync for {synced_count} active users"

    except Exception as e:
        logger.error(f"Error in bulk_sync_newsfeed_caches: {str(e)}")
        return f"Error: {str(e)}"

