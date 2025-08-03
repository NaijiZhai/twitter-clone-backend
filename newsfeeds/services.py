from datetime import datetime

from django.contrib.auth.models import User
from django.db import connection

from cache_utils.cache_constants import NEWSFEED_USER_PATTERN
from cache_utils.redis_helper import RedisHelper
from friendships.services import FriendshipServices
from newsfeeds.models import NewsFeed
from newsfeeds.tasks import fanout_newsfeeds_main_task, sync_newsfeed_cache_task
from tweets.models import Tweet

# threshold
HYBRID_MODE_THRESHOLD = 5000
MAX_POSSIBLE_SCAN = 100


class NewsFeedService(object):
    @classmethod
    def fanout_to_followers(cls, tweet: Tweet, created_at=None):
        """
        fan_out
        """
        followers_count = FriendshipServices.get_followers(tweet.user_id).count()

        if followers_count <= HYBRID_MODE_THRESHOLD:
            # use push for normal user
            fanout_newsfeeds_main_task.delay(tweet.id, tweet.created_at.isoformat(), tweet.user_id)
        else:
            # use pull for celebrities
            NewsFeed.objects.create(
                user_id=tweet.user_id,
                tweet=tweet,
                created_at=created_at or tweet.created_at
            )
            # cache for active user
            # cls.trigger_cache_sync_for_active_followers(tweet.user_id)

    @classmethod
    def inject_newsfeed(cls, from_user_id: int, to_user_id: int):
        """

        """
        followers_count = FriendshipServices.get_followers(to_user_id).count()
        tweets = Tweet.objects.filter(user_id=to_user_id).order_by('-created_at')[:3]
        if not tweets:
            return

        last_newsfeed_in_cache = RedisHelper.get_last_obj_in_cache(NEWSFEED_USER_PATTERN.format(user_id=from_user_id))
        if last_newsfeed_in_cache:
            if last_newsfeed_in_cache.get('fields', {}).get('is_pull_mode'):
                creat_at = last_newsfeed_in_cache.get('fields', {}).get('created_at')
                creat_at = datetime.fromisoformat(creat_at) if isinstance(creat_at, str) else creat_at
                if creat_at and creat_at >= tweets[0].created_at:
                    return
            else:
                if last_newsfeed_in_cache.created_at >= tweets[0].created_at:
                    return

        if followers_count <= HYBRID_MODE_THRESHOLD:
            # create newsfeeds
            tweets = Tweet.objects.filter(user_id=to_user_id).order_by('-created_at')[:3]
            newsfeeds = [NewsFeed(user_id=from_user_id, tweet=tweet) for tweet in tweets]
            NewsFeed.objects.bulk_create(newsfeeds)
        sync_newsfeed_cache_task.delay(from_user_id)

    @classmethod
    def remove_newsfeed(cls, from_user: User, to_user: User):
        """
        Remove newsfeed for user
        """
        NewsFeed.objects.filter(user_id=to_user, tweet__user=from_user).delete()
        key = NEWSFEED_USER_PATTERN.format(user_id=to_user)
        RedisHelper.invalidate_cache(key)

    @classmethod
    def get_cached_newsfeed(cls, user_id):
        """
        get_cached_newsfeed
        """
        key = NEWSFEED_USER_PATTERN.format(user_id=user_id)
        return RedisHelper.get_newsfeeds_from_redis(key, user_id, model=NewsFeed)

    @classmethod
    def push_newsfeed_to_cache(cls, newsfeed):
        """
        push newsfeed to cache
        """
        key = NEWSFEED_USER_PATTERN.format(user_id=newsfeed.user_id)
        RedisHelper.push_obj(key, newsfeed, NewsFeed)

    @classmethod
    def get_newsfeed_hybrid(cls, user_id, max_tweet_id=None, count=100, created_at_lt=None, created_at_gt=None):
        """
        Hybrid caching strategy for Twitter timeline system

        Philosophy: Cache serves performance optimization, not data consistency.
        Different user actions require different data freshness guarantees.

        Args:
            user_id: Target user ID
            max_tweet_id: Maximum tweet ID for pagination (optional)
            count: Number of tweets to return
            created_at_lt: Get tweets older than this timestamp (infinite scroll)
            created_at_gt: Get tweets newer than this timestamp (pull-to-refresh)

        Returns:
            List of tweets based on caching strategy
        """

        # Pull-to-refresh Strategy (created_at_gt):
        # - Always query DB directly, bypass cache entirely
        # - Ensures users get latest tweets on explicit refresh action
        # - Cache doesn't guarantee real-time updates
        if created_at_gt:
            # Never use cache for latest tweets - always hit DB for freshness
            return cls._get_newsfeeds_from_db_and_pull(
                user_id, max_tweet_id, count, created_at_lt, created_at_gt
            )

        # Homepage Loading & Infinite Scroll Strategy:
        # - Cache-first approach for fast initial load and historical content
        # - Fallback to DB when cache miss or insufficient data
        # - Prioritizes user experience over absolute freshness

        # Step 1: Try to get cached timeline (top 100 tweets for active users)
        cached_feeds = cls.get_cached_newsfeed(user_id)

        # Step 2: Validate cache integrity and apply filters
        if cached_feeds and cls._validate_cache_order(cached_feeds):
            # Filter cached tweets based on pagination parameters
            # For infinite scroll (created_at_lt): get older tweets from cache
            # For homepage: get most recent cached tweets
            filtered_feeds = cls._filter_cached_feeds(
                cached_feeds, max_tweet_id, created_at_lt, created_at_gt, count
            )

            # Step 3: Cache hit with sufficient data - return immediately
            if len(filtered_feeds) >= count:
                # Fast path: return cached results for optimal performance
                return filtered_feeds[:count]

        # Step 4: Cache miss or insufficient cached data - fallback to DB
        # This handles:
        # - New users without cached timeline
        # - Cache expiration or invalidation
        # - Requesting more data than available in cache
        # - Cache corruption or inconsistency
        return cls._get_newsfeeds_from_db_and_pull(
            user_id, max_tweet_id, count, created_at_lt, created_at_gt
        )

    @classmethod
    def _filter_cached_feeds(cls, cached_feeds, max_tweet_id=None, created_at_lt=None, created_at_gt=None, count=100):
        """
        filter cached newsfeeds based on pagination parameters
        """
        filtered = []

        for feed in cached_feeds:
            #  created_at_gt for new feeds
            if created_at_gt and feed.created_at <= created_at_gt:
                continue

            # created_at_lt for older feeds
            if created_at_lt and feed.created_at >= created_at_lt:
                continue

            #  max_tweet_id
            if max_tweet_id:
                tweet_id = getattr(feed, 'tweet_id', feed.tweet.id if feed.tweet else 0)
                if tweet_id >= max_tweet_id:
                    continue

            filtered.append(feed)

            # we have enough
            if len(filtered) >= count:
                break

        return filtered

    @classmethod
    def _get_newsfeeds_from_db_and_pull(cls, user_id, max_tweet_id, count, created_at_lt, created_at_gt):
        """get newsfeeds from db and pull"""
        following_ids = FriendshipServices.get_following_id_set(user_id)
        following_ids.add(user_id)

        high_follower_users, normal_users = cls._categorize_following_users(following_ids)

        newsfeeds = []

        if normal_users:
            db_feeds = cls._get_db_newsfeeds(
                user_id, normal_users, max_tweet_id, count,
                created_at_lt=created_at_lt, created_at_gt=created_at_gt
            )
            newsfeeds.extend(db_feeds)

        if high_follower_users:
            pull_tweets = cls._get_pull_tweets(
                high_follower_users, max_tweet_id, count,
                created_at_lt=created_at_lt, created_at_gt=created_at_gt
            )

            for tweet in pull_tweets:
                pseudo_newsfeed = RedisHelper.create_pseudo_newsfeed(tweet, user_id)
                newsfeeds.append(pseudo_newsfeed)

        newsfeeds.sort(key=lambda x: (-x.created_at.timestamp(), -x.tweet_id))
        return newsfeeds[:count]

    @classmethod
    def _categorize_following_users(cls, following_ids):
        """
        categorize users based on their follower counts
        """
        if not following_ids:
            return [], []

        # qs = Friendship.objects.filter(to_user_id__in=following_ids) \
        #     .values('to_user_id') \
        #     .annotate(follower_count=Count('from_user'))
        #
        # user_follower_counts = {row['to_user_id']: row['follower_count'] for row in qs}

        # query followers
        with connection.cursor() as cursor:
            cursor.execute("""
                           SELECT to_user_id, COUNT(*) as follower_count
                           FROM friendships_friendship
                           WHERE to_user_id IN %s
                           GROUP BY to_user_id
                           """, [tuple(following_ids)])

            user_follower_counts = dict(cursor.fetchall())

        high_follower_users = []
        normal_users = []

        for user_id in following_ids:
            follower_count = user_follower_counts.get(user_id, 0)
            if follower_count > HYBRID_MODE_THRESHOLD:
                high_follower_users.append(user_id)
            else:
                normal_users.append(user_id)

        return high_follower_users, normal_users

    @classmethod
    def _get_db_newsfeeds(cls, user_id, user_ids, max_tweet_id, count, created_at_lt=None, created_at_gt=None):
        """get db newsfeeds from db"""
        queryset = NewsFeed.objects.filter(
            user_id=user_id,
            tweet__user_id__in=user_ids
        )

        if max_tweet_id:
            queryset = queryset.filter(tweet_id__lt=max_tweet_id)
        if created_at_lt:
            queryset = queryset.filter(created_at__lt=created_at_lt)
        if created_at_gt:
            queryset = queryset.filter(created_at__gt=created_at_gt)

        return list(queryset.order_by('-created_at')[:count])

    @classmethod
    def _get_pull_tweets(cls, user_ids, max_tweet_id, count, created_at_lt=None, created_at_gt=None):
        """get pull tweets from db"""
        queryset = (
            Tweet.objects
            .filter(user_id__in=user_ids)
            .filter(**({'id__lt': max_tweet_id} if max_tweet_id else {}))
            .filter(**({'created_at__lt': created_at_lt} if created_at_lt else {}))
            .filter(**({'created_at__gt': created_at_gt} if created_at_gt else {}))
            .order_by('-created_at', '-id')[:MAX_POSSIBLE_SCAN]
        )

        return list(queryset.select_related('user')[:count])

    @classmethod
    def _validate_cache_order(cls, cached_feeds):
        """
        validate the order of cached newsfeeds
        """
        if len(cached_feeds) < 2:
            return True

        for i in range(len(cached_feeds) - 1):
            current = cached_feeds[i]
            next_item = cached_feeds[i + 1]

            current_time = current.created_at.timestamp()
            next_time = next_item.created_at.timestamp()

            # reverse chronological order
            if current_time < next_time:
                return False
            elif current_time == next_time:
                # same time id should be decreasing order
                current_id = getattr(current, 'tweet_id', current.id)
                next_id = getattr(next_item, 'tweet_id', next_item.id)
                if current_id < next_id:
                    return False

        return True
