import uuid
from datetime import datetime

from celery import shared_task
from celery.utils.log import logger

from friendships.services import FriendshipServices
from newsfeeds.models import NewsFeed
from celery import shared_task

from friendships.services import FriendshipServices
from newsfeeds.models import NewsFeed
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
            logger.error(f'Error dispatching fanout batch: {e}')
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
