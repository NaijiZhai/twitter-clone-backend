from cache_utils.redis_helper import RedisHelper
from friendships.services import FriendshipServices
from tweets.models import Tweet
from friendships.models import Friendship
from django.contrib.auth.models import User
from newsfeeds.models import NewsFeed
from cache_utils.cache_constants import NEWSFEED_USER_PATTERN


class NewsFeedService(object):
    @classmethod
    def fanout_to_followers(cls, tweet: Tweet):
        followers = FriendshipServices.get_followers(tweet = tweet)
        newsfeeds = [NewsFeed(user = follower, tweet = tweet) for follower in followers]
        newsfeeds.append(NewsFeed(user = tweet.user, tweet = tweet))
        NewsFeed.objects.bulk_create(newsfeeds)
        #bulk_create would not trigger post_save
        for newsfeed in newsfeeds:
            NewsFeedService.push_newsfeed_to_cache(newsfeed)

    @classmethod
    def inject_newsfeed(cls, from_user : User, to_user : User):
        tweets = Tweet.objects.filter(user_id = from_user).order_by('-created_at')[:3]
        newsfeeds = [NewsFeed(user_id = to_user, tweet= tweet) for tweet in tweets]
        NewsFeed.objects.bulk_create(newsfeeds)


    @classmethod
    def remove_newsfeed(cls, from_user : User, to_user : User):
        NewsFeed.objects.filter(user_id = to_user, tweet__user = from_user).delete()

    @classmethod
    def get_cached_newsfeed(cls, user_id):
        queryset = NewsFeed.objects.filter(user_id=user_id).order_by('-created_at')
        key = NEWSFEED_USER_PATTERN.format(user_id=user_id)
        return RedisHelper.get_from_redis(key, queryset)

    @classmethod
    def push_newsfeed_to_cache(cls, newsfeed):
        queryset = NewsFeed.objects.filter(user_id=newsfeed.user_id).order_by('-created_at')
        key = NEWSFEED_USER_PATTERN.format(user_id=newsfeed.user_id)
        RedisHelper.push_obj(key, newsfeed, queryset)
