import redis
from django.conf import settings
from utils.cache_constants import REDIS_KEY_EXPIRE_TIME, REDIS_DB, REDIS_HOST, REDIS_PORT

class RedisClient:
    conn = None

    @classmethod
    def get_connection(cls):
        if not cls.conn:
            cls.conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        return cls.conn

    @classmethod
    def clear(cls):
        if not settings.TESTING:
            raise Exception("Can't clear connection in production")
        if cls.conn:
            cls.conn.flushdb()
