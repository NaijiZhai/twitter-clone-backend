import time
import uuid
from datetime import datetime, timedelta

from celery import shared_task
from celery.utils.log import logger
from django.contrib.auth.models import User
from django.utils import timezone

from cache_utils.cache_constants import REDIS_LIST_LIMIT_LENGTH
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
    batch_count = 0

    while index < len(follower_ids):
        batch_ids = follower_ids[index: index + FANOUT_BATCH_SIZE]
        try:
            if batch_count == 0:
                # run first batch immediately
                fanout_newsfeeds_batch_task.delay(tweet_id, created_at.isoformat(), batch_ids)
            else:
                # delay each batch
                eta = timezone.now() + timedelta(seconds=batch_count * 0.1)  # delay 100ms for each batch
                fanout_newsfeeds_batch_task.apply_async(
                    args=(tweet_id, created_at.isoformat(), batch_ids),
                    eta=eta
                )
        except Exception as e:
            logger.error(f'Error dispatching fanout batch: {e}, batch_ids: {batch_ids}')

        index += FANOUT_BATCH_SIZE
        batch_count += 1

    return '{} newsfeeds going to fanout, {} batches created.'.format(
        len(follower_ids),
        batch_count,
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


@shared_task(queue='HighPriority')
def batch_sync_active_users_cache():
    """
    Batch sync cache for all active users
    Triggered by Celery Beat schedule
    """
    recent_time = timezone.now() - timedelta(days=1)
    active_users = User.objects.filter(
        last_login__gte=recent_time
    ).values_list('id', flat=True)

    if not active_users:
        logger.info("No active users found for cache sync")
        return "No active users found"

    logger.info(f"Starting batch cache sync for {len(active_users)} active users")

    successful_tasks = 0
    failed_tasks = 0

    # batch_create
    batch_size = 100
    for i in range(0, len(active_users), batch_size):
        batch = active_users[i:i + batch_size]

        for user_id in batch:
            try:
                # avoid running at same time to crash redis
                eta = timezone.now() + timedelta(seconds=successful_tasks * 0.2)
                sync_newsfeed_cache_task.apply_async(
                    args=(user_id,),
                    eta=eta,
                    queue='LowPriority'
                )
                successful_tasks += 1

            except Exception as e:
                logger.error(f"Error scheduling cache sync for user {user_id}: {e}")
                failed_tasks += 1

        # small delay
        time.sleep(1)

    logger.info(f"Batch sync completed: {successful_tasks} scheduled, {failed_tasks} failed")
    return f"Batch sync: {successful_tasks} scheduled, {failed_tasks} failed"


@shared_task(queue='LowPriority')
def sync_newsfeed_cache_task(user_id):
    """
    sync_newsfeed_cache
    """
    try:
        following_ids = FriendshipServices.get_following_id_set(user_id)
        following_ids.add(user_id)

        # get lastest tweets
        recent_tweets = Tweet.objects.filter(
            user_id__in=following_ids,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).select_related('user').order_by('-created_at', '-id')[:REDIS_LIST_LIMIT_LENGTH]

        if not recent_tweets:
            return f"No recent tweets for user {user_id}"

        # batch query to avoid n+1 query
        tweet_ids = [tweet.id for tweet in recent_tweets]
        existing_newsfeeds = NewsFeed.objects.filter(
            user_id=user_id,
            tweet_id__in=tweet_ids
        ).select_related('tweet', 'tweet__user')

        # created map for fast query
        existing_newsfeed_map = {nf.tweet_id: nf for nf in existing_newsfeeds}

        # update cache
        from cache_utils.cache_constants import NEWSFEED_USER_PATTERN
        from cache_utils.redis_helper import RedisHelper

        key = NEWSFEED_USER_PATTERN.format(user_id=user_id)
        RedisHelper.invalidate_cache(key)

        from newsfeeds.services import NewsFeedService
        cached_newsfeeds = []

        for tweet in recent_tweets:
            existing_newsfeed = existing_newsfeed_map.get(tweet.id)

            if existing_newsfeed:
                cached_newsfeeds.append(existing_newsfeed)
            else:
                pseudo_newsfeed = RedisHelper.create_pseudo_newsfeed(tweet, user_id=user_id)
                cached_newsfeeds.append(pseudo_newsfeed)

        RedisHelper.load_newsfeeds_to_cache_ordered(NEWSFEED_USER_PATTERN.format(user_id), cached_newsfeeds)

        return f"Synced cache for user {user_id} with {len(recent_tweets)} tweets"

    except Exception as e:
        logger.error(f"Error syncing cache for user {user_id}: {str(e)}")
        return f"Error syncing cache for user {user_id}: {str(e)}"
