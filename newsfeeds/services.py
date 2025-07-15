import uuid

from django.contrib.auth.models import User

from cache_utils.cache_constants import NEWSFEED_USER_PATTERN
from cache_utils.redis_helper import RedisHelper
from friendships.services import FriendshipServices
from newsfeeds.models import NewsFeed
from newsfeeds.tasks import fanout_newsfeed
from tweets.models import Tweet


class NewsFeedService(object):
    @classmethod
    def fanout_to_followers(cls, tweet: Tweet):
        # followers = FriendshipServices.get_followers(tweet=tweet)
        # insert_tag = str(uuid.uuid4())
        # newsfeeds = [NewsFeed(user=follower, tweet=tweet, insert_tag = insert_tag) for follower in followers]
        # newsfeeds.append(NewsFeed(user=tweet.user, tweet=tweet, insert_tag = insert_tag))
        # # bulk_create doesn't not return an id!!!!
        # # NewsFeed.objects.bulk_create(newsfeeds)
        #
        # # version 2, bulk_create would not trigger post_save, but this is n+1 query which is very bad.
        # # for newsfeed in newsfeeds:
        # #     # print(newsfeed.id)
        # #     newsfeed.save()
        #
        # # final solution, I add a field in the model for lookup
        # NewsFeed.objects.bulk_create(newsfeeds)
        # newsfeeds = NewsFeed.objects.filter(insert_tag=insert_tag)
        # for newsfeed in newsfeeds:
        #     NewsFeedService.push_newsfeed_to_cache(newsfeed)

        #use mq for async process, use id because:
        #kombu.exceptions.EncodeError: Object of type Tweet is not JSON serializable

        fanout_newsfeed.delay(tweet.id)




    @classmethod
    def inject_newsfeed(cls, from_user: User, to_user: User):
        tweets = Tweet.objects.filter(user_id=from_user).order_by('-created_at')[:3]
        newsfeeds = [NewsFeed(user_id=to_user, tweet=tweet) for tweet in tweets]
        NewsFeed.objects.bulk_create(newsfeeds)

    @classmethod
    def remove_newsfeed(cls, from_user: User, to_user: User):
        NewsFeed.objects.filter(user_id=to_user, tweet__user=from_user).delete()

    @classmethod
    def get_cached_newsfeed(cls, user_id):
        key = NEWSFEED_USER_PATTERN.format(user_id=user_id)
        return RedisHelper.get_from_redis(key, user_id, model = NewsFeed)

    @classmethod
    def push_newsfeed_to_cache(cls, newsfeed):
        key = NEWSFEED_USER_PATTERN.format(user_id=newsfeed.user_id)
        RedisHelper.push_obj(key, newsfeed, NewsFeed)
