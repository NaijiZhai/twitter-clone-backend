from cache_utils.cache_constants import USER_TWEETS_PATTERN
from cache_utils.redis_helper import RedisHelper
from tweets.models import TweetPhoto, Tweet


class TweetService(object):

    @classmethod
    def create_photos(cls, tweet: Tweet, photos):
        photo_files = []
        for idx, photo in enumerate(photos):
            photo_files.append(TweetPhoto(tweet=tweet, user=tweet.user, file=photo, order=idx))

        TweetPhoto.objects.bulk_create(photo_files)

    @classmethod
    def get_cached_tweets(cls, user_id):
        key = USER_TWEETS_PATTERN.format(user_id=user_id)
        tweets = RedisHelper.get_from_redis(key, user_id, model = Tweet)

        return tweets


    @classmethod
    def push_tweets_to_cache(cls, tweet):
        key = USER_TWEETS_PATTERN.format(user_id=tweet.user_id)
        RedisHelper.push_obj(key, tweet, Tweet)
