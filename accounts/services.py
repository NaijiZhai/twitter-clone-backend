from django.conf import settings
from django.core.cache import caches
from django.db import transaction, IntegrityError

from accounts.models import UserProfile
from cache_utils.cache_constants import USERPROFILE_PATTERN

cache = caches['testing'] if settings.TESTING else caches['default']


class UserServices:


    @classmethod
    def get_userprofile_by_user_id_through_cache(cls, user_id):
        key = USERPROFILE_PATTERN.format(user_id=user_id)
        if cache:
            userprofile = cache.get(key)
            if userprofile:
                return userprofile

        userprofile = cls._get_or_create_user_profile(user_id)

        if cache and userprofile:
            cache.set(key, userprofile)
        return userprofile

    @classmethod
    def invalidate_userprofile_cache(cls, user_id):
        key = USERPROFILE_PATTERN.format(user_id=user_id)
        cache.delete(key)

    def _get_or_create_user_profile(user_id):
        try:
            with transaction.atomic():
                userprofile, _ = UserProfile.objects.select_for_update().get_or_create(user_id=user_id)
                return userprofile
        except IntegrityError:
            # Handle race condition
            return UserProfile.objects.get(user_id=user_id)
