import cache_utils.cache_constants
from cache_utils.redis_client import RedisClient
from cache_utils.redis_serializer import RedisSerializer


class RedisHelper:

    @classmethod
    def push_obj(cls, key, obj, queryset):
        conn = RedisClient.get_connection()
        if not conn.exists(key):
            cls._load_objects_to_cache(key, queryset)
            return
        serialized_data = RedisSerializer.serialize(obj)
        conn.lpush(key, serialized_data)
        conn.ltrim(key, 0, cache_utils.cache_constants.REDIS_LIST_LIMIT_LENGTH - 1)

    @classmethod
    def get_from_redis(cls, key, queryset):
        conn = RedisClient.get_connection()

        if conn.exists(key):
            serialized_list = conn.lrange(key, 0, -1)
            objects = []
            for serialized_data in serialized_list:
                obj = RedisSerializer.deserialize(serialized_data)
                objects.append(obj)
            return objects

        cls._load_objects_to_cache(key, queryset)
        return list(queryset)

    @classmethod
    def _load_objects_to_cache(cls, key, queryset):
        conn = RedisClient.get_connection()
        objects = []
        for obj in queryset[:cache_utils.cache_constants.REDIS_LIST_LIMIT_LENGTH]:
            serialized_data = RedisSerializer.serialize(obj)
            objects.append(serialized_data)
        if objects:
            conn.rpush(key, *objects)
            conn.expire(key, cache_utils.cache_constants.REDIS_KEY_EXPIRE_TIME)