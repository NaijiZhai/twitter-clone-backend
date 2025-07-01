from django.conf import settings

FOLLOWING_PATTERN = 'followings of {user_id}'
USER_PATTERN = 'user: {user_id}'
USERPROFILE_PATTERN = 'userprofile: {user_id}'
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 2 if settings.TESTING else 3
REDIS_KEY_EXPIRE_TIME = 60 * 60 * 24