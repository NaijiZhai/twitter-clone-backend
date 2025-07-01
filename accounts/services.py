from django.conf import settings
from django.core.cache import caches

from accounts.models import UserProfile
from utils.cache_constants import USERPROFILE_PATTERN

cache = caches['testing'] if settings.TESTING else caches['default']


class UserServices:


    @classmethod
    def get_userprofile_by_user_id_through_cache(cls, user_id):
        key = USERPROFILE_PATTERN.format(user_id=user_id)
        if cache:
            userprofile = cache.get(key)
            if userprofile:
                return userprofile
        userprofile, _ = UserProfile.objects.get_or_create(user_id=user_id)
        if cache and userprofile:
            cache.set(key, userprofile)
        return userprofile

    @classmethod
    def invalidate_userprofile_cache(cls, user_id):
        key = USERPROFILE_PATTERN.format(user_id=user_id)
        cache.delete(key)
