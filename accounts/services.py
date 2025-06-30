from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import caches

from accounts.models import UserProfile
from twitter.cache_constants import USER_PATTERN, USERPROFILE_PATTERN

cache = caches['default'] if settings.TESTING else None


class UserServices:

    @classmethod
    def get_user_by_id_through_cache(cls, user_id):
        key = USER_PATTERN.format(user_id=user_id)
        if cache:
            user = cache.get(key)
            if user:
                return user
        user = User.objects.get(id=user_id)
        if cache and user:
            cache.set(key, user)
        return user

    @classmethod
    def invalidate_user_cache(cls, user_id):
        key = USER_PATTERN.format(user_id=user_id)
        cache.delete(key)

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
