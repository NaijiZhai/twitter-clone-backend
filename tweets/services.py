from tweets.models import TweetPhoto, Tweet
from cache_utils.cache_constants import USER_TWEETS_PATTERN
from cache_utils.redis_helper import RedisHelper


class TweetService(object):

    @classmethod
    def create_photos(cls, tweet : Tweet, photos):
        photo_files = []
        for idx, photo in enumerate(photos):
            photo_files.append(TweetPhoto(tweet = tweet, user = tweet.user, file = photo, order=idx))

        TweetPhoto.objects.bulk_create(photo_files)

    @classmethod
    def get_cached_tweets(cls, user_id):
        query = Tweet.objects.filter(user_id=user_id).order_by('-created_at')
        key = USER_TWEETS_PATTERN.format(user_id=user_id)
        return RedisHelper.get_from_redis(key, query)


    @classmethod
    def push_tweets_to_cache(cls, tweet):
        query = Tweet.objects.filter(user_id=tweet.user_id).order_by('-created_at')
        key = USER_TWEETS_PATTERN.format(user_id=tweet.user_id)
        RedisHelper.push_obj(key, tweet, query)
