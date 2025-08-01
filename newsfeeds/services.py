import uuid
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q
from django.db import connection

from cache_utils.cache_constants import NEWSFEED_USER_PATTERN
from cache_utils.redis_helper import RedisHelper
from friendships.services import FriendshipServices
from newsfeeds.models import NewsFeed
from newsfeeds.tasks import fanout_newsfeeds_main_task, sync_newsfeed_cache_task
from tweets.models import Tweet

# threshold
HYBRID_MODE_THRESHOLD = 0
CACHE_SYNC_INTERVAL_HOURS = 6


class NewsFeedService(object):
    @classmethod
    def fanout_to_followers(cls, tweet: Tweet, created_at=None):
        """
        发推文时的fanout策略
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
            cls.trigger_cache_sync_for_active_followers(tweet.user_id)

    @classmethod
    def inject_newsfeed(cls, from_user_id: int, to_user_id: int):
        """
        关注时注入历史推文
        from_user_id: 关注者ID
        to_user_id: 被关注者ID
        """
        followers_count = FriendshipServices.get_followers(to_user_id).count()

        if followers_count <= HYBRID_MODE_THRESHOLD:
            # 关注的是普通用户：从NewsFeed表找历史推文，或创建NewsFeed记录
            tweets = Tweet.objects.filter(user_id=to_user_id).order_by('-created_at')[:3]
            newsfeeds = [NewsFeed(user_id=from_user_id, tweet=tweet) for tweet in tweets]
            NewsFeed.objects.bulk_create(newsfeeds)

            # 更新缓存
            for newsfeed in newsfeeds:
                cls.push_newsfeed_to_cache(newsfeed)
        else:
            # 关注的是大V用户：不创建历史NewsFeed，触发缓存更新即可
            sync_newsfeed_cache_task.delay(from_user_id)

    @classmethod
    def remove_newsfeed(cls, from_user: User, to_user: User):
        """
        取消关注时移除newsfeed
        """
        NewsFeed.objects.filter(user_id=to_user, tweet__user=from_user).delete()
        # 清除缓存，强制下次重新计算
        key = NEWSFEED_USER_PATTERN.format(user_id=to_user)
        RedisHelper.invalidate_cache(key)

    @classmethod
    def get_cached_newsfeed(cls, user_id):
        """
        获取缓存的newsfeed
        """
        key = NEWSFEED_USER_PATTERN.format(user_id=user_id)
        return RedisHelper.get_from_redis(key, user_id, model=NewsFeed)

    @classmethod
    def push_newsfeed_to_cache(cls, newsfeed):
        """
        将newsfeed推送到缓存
        """
        key = NEWSFEED_USER_PATTERN.format(user_id=newsfeed.user_id)
        RedisHelper.push_obj(key, newsfeed, NewsFeed)

    @classmethod
    def get_newsfeed_hybrid(cls, user_id, max_tweet_id=None, count=100, created_at_lt=None, created_at_gt=None):
        """
        混合模式获取newsfeed - 简化版
        """
        # 🔍 重要：如果有分页参数，不使用缓存，直接查询
        if created_at_lt or max_tweet_id:
            return cls._get_newsfeeds_from_db_and_pull(
                user_id, max_tweet_id, count, created_at_lt, created_at_gt
            )

        # 只有请求最新数据时才使用缓存
        if not created_at_gt:  # 请求最新数据
            cached_feeds = cls.get_cached_newsfeed(user_id)
            if cached_feeds and cls._validate_cache_order(cached_feeds):
                if len(cached_feeds) >= count:
                    return cached_feeds[:count]

        # 缓存不够或请求特定时间范围，使用混合模式
        return cls._get_newsfeeds_from_db_and_pull(
            user_id, max_tweet_id, count, created_at_lt, created_at_gt
        )

    @classmethod
    def _get_newsfeeds_from_db_and_pull(cls, user_id, max_tweet_id, count, created_at_lt, created_at_gt):
        """从数据库和pull模式获取newsfeeds"""
        following_ids = FriendshipServices.get_following_id_set(user_id)
        following_ids.add(user_id)

        high_follower_users, normal_users = cls._categorize_following_users(following_ids)

        newsfeeds = []

        if normal_users:
            db_feeds = cls._get_db_newsfeeds(
                user_id, normal_users, max_tweet_id, count,  # 不要乘以2，直接传count
                created_at_lt=created_at_lt, created_at_gt=created_at_gt
            )
            newsfeeds.extend(db_feeds)

        if high_follower_users:
            pull_tweets = cls._get_pull_tweets(
                high_follower_users, max_tweet_id, count,  # 不要乘以2
                created_at_lt=created_at_lt, created_at_gt=created_at_gt
            )

            for tweet in pull_tweets:
                pseudo_newsfeed = RedisHelper._create_pseudo_newsfeed(tweet, user_id)
                newsfeeds.append(pseudo_newsfeed)

        newsfeeds.sort(key=lambda x: (-x.created_at.timestamp(), -x.tweet_id))
        return newsfeeds[:count]

    @classmethod
    def _build_cache_from_result(cls, user_id, newsfeeds):
        """
        从查询结果建立缓存
        """
        # 清除旧缓存
        key = NEWSFEED_USER_PATTERN.format(user_id=user_id)
        RedisHelper.invalidate_cache(key)

        # 建立新缓存 - 注意要按正确顺序推入
        for newsfeed in reversed(newsfeeds):  # 反向推入以保持正确顺序
            cls.push_newsfeed_to_cache(newsfeed)

    @classmethod
    def _categorize_following_users(cls, following_ids):
        """
        将关注用户分为高关注度和普通用户
        """
        if not following_ids:
            return [], []

        # 使用SQL查询获取每个用户的关注者数量
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
        """获取数据库中的newsfeeds"""
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
        """获取pull模式的推文"""
        queryset = Tweet.objects.filter(user_id__in=user_ids)

        if max_tweet_id:
            queryset = queryset.filter(id__lt=max_tweet_id)
        if created_at_lt:
            queryset = queryset.filter(created_at__lt=created_at_lt)
        if created_at_gt:
            queryset = queryset.filter(created_at__gt=created_at_gt)

        return list(queryset.select_related('user').order_by('-created_at')[:count])

    @classmethod
    def _validate_cache_order(cls, cached_feeds):
        """
        验证缓存中的newsfeed是否按正确顺序排列
        """
        if len(cached_feeds) < 2:
            return True

        for i in range(len(cached_feeds) - 1):
            current = cached_feeds[i]
            next_item = cached_feeds[i + 1]

            current_time = current.created_at.timestamp()
            next_time = next_item.created_at.timestamp()

            # 时间应该是递减的
            if current_time < next_time:
                return False
            elif current_time == next_time:
                # 时间相同时，ID应该是递减的
                current_id = getattr(current, 'tweet_id', current.id)
                next_id = getattr(next_item, 'tweet_id', next_item.id)
                if current_id < next_id:
                    return False

        return True

    @classmethod
    def trigger_cache_sync_for_active_followers(cls, high_follower_user_id):
        """
        cache for active followers
        """
        # get active user (those loggined in for the past 1 day)
        recent_time = timezone.now() - timedelta(days=1)
        active_followers = User.objects.filter(
            friendship_follower_set__to_user_id=high_follower_user_id,  # search for active followers
            last_login__gte=recent_time
        ).values_list('id', flat=True)

        # batch cache
        for follower_id in active_followers:
            try:
                sync_newsfeed_cache_task.delay(follower_id)
            except Exception as e:
                # record errors
                print(f"Error triggering cache sync for follower {follower_id}: {e}")
