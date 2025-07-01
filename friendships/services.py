from django.conf import settings
from django.core.cache import caches

from friendships.models import Friendship
from tweets.models import Tweet
from utils.cache_constants import FOLLOWING_PATTERN

cache = caches['testing'] if settings.TESTING else caches['default']


class FriendshipServices(object):
    @classmethod
    def get_followers(cls, tweet : Tweet):
        friendships  = Friendship.objects.filter(to_user=tweet.user).prefetch_related('from_user')
        return [friendship.from_user for friendship in friendships]


    @classmethod
    def get_following_id_set(cls, user_id):
        cache_key = FOLLOWING_PATTERN.format(user_id=user_id)
        if cache.get(cache_key):
            return cache.get(cache_key)
        following_id_set = set(
            Friendship.objects.filter(from_user_id=user_id).values_list('to_user_id', flat=True))
        cache.set(cache_key, following_id_set)
        return following_id_set

    @classmethod
    def invalidate_following_cache(cls, user_id):
        key = FOLLOWING_PATTERN.format(user_id=user_id)
        cache.delete(key)

