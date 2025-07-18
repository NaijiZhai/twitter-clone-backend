from django.conf import settings
from django.core.cache import cache, caches

from cache_utils import cache_constants
from cache_utils.cache_utils import CacheUtils
from cache_utils.redis_client import RedisClient
from cache_utils.redis_serializer import RedisSerializer
cache = caches['testing'] if settings.TESTING else caches['default']

class RedisHelper:

    @classmethod
    def push_obj(cls, key, obj, model):
        conn = RedisClient.get_connection()
        if not conn.exists(key):
            queryset = model.objects.filter(user=obj.user).order_by('-created_at').values_list('id', flat=True)
            cls._load_objects_to_cache(key, queryset, model)
            return
        conn.lpush(key, obj.id)
        conn.ltrim(key, 0, cache_constants.REDIS_LIST_LIMIT_LENGTH - 1)

    @classmethod
    def get_from_redis(cls, key, user_id, model=None):
        conn = RedisClient.get_connection()

        if conn.exists(key):
            id_list = conn.lrange(key, 0, -1)
            # [b'3', b'2', b'1']
            id_list = [int(obj_id) for obj_id in id_list]
            keys = [CacheUtils.get_key(model, obj_id) for obj_id in id_list]
            cache_results = CacheUtils.get_many(keys)
            objects = []
            missed_ids = []
            missed_idx = []
            for obj_id, key in zip(id_list, keys):

                obj = cache_results.get(key)
                if obj:
                    if isinstance(obj, str):
                        obj = RedisSerializer.deserialize(obj)
                    objects.append(obj)
                else:
                    missed_ids.append(obj_id)
                    missed_idx.append(len(objects))
                    objects.append(None)

            if missed_ids:
                db_objs = model.objects.filter(id__in=missed_ids)
                obj_map = {obj.id: obj for obj in db_objs}
                cache_data = {
                    CacheUtils.get_key(model, obj.id): obj
                    for obj in db_objs
                }
                cache.set_many(cache_data)
                for obj_id, idx in zip(missed_ids, missed_idx):
                    obj = obj_map.get(obj_id)
                    if isinstance(obj, str):
                        obj = RedisSerializer.deserialize(obj)
                    objects[idx] = obj

            # for serialized_data in serialized_list:
            #     obj = RedisSerializer.deserialize(serialized_data)
            #     objects.append(obj)
            return objects

        queryset = model.objects.filter(user_id=user_id).order_by('-created_at')
        cls._load_objects_to_cache(key, queryset.values_list('id', flat=True), model)
        return list(queryset)

    @classmethod
    def _load_objects_to_cache(cls, key, queryset, model=None):
        conn = RedisClient.get_connection()
        objects = []
        for obj in queryset[:cache_constants.REDIS_LIST_LIMIT_LENGTH]:
            if obj:
                objects.append(obj)
        if objects:
            conn.rpush(key, *objects)
            conn.expire(key, cache_constants.REDIS_KEY_EXPIRE_TIME)


    @classmethod
    def invalidate_cache(cls, key):
        conn = RedisClient.get_connection()
        conn.delete(key)

    @classmethod
    def get_key_for_count(cls, obj, attr):
        return f"{obj.__class__.__name__}.{attr}:{obj.id}"

    # @classmethod
    # def increment_count(cls, obj, attr, already_incremented_in_db = False):
    #     key = cls.get_key_for_count(obj, attr)
    #     conn = RedisClient.get_connection()
    #     if not conn.exists(key):
    #         obj.refresh_from_db()
    #         conn.set(key, getattr(obj, attr))
    #         conn.expire(key, cache_constants.REDIS_KEY_EXPIRE_TIME)
    #         # increment has been made in db.
    #         return getattr(obj, attr)
    #     return conn.incr(key)
    #
    # @classmethod
    # def decrement_count(cls, obj, attr, already_decremented_in_db = False):
    #     key = cls.get_key_for_count(obj, attr)
    #     conn = RedisClient.get_connection()
    #     if not conn.exists(key):
    #         obj.refresh_from_db()
    #         conn.set(key, getattr(obj, attr))
    #         conn.expire(key, cache_constants.REDIS_KEY_EXPIRE_TIME)
    #         return getattr(obj, attr)
    #     return conn.decr(key)

    @classmethod
    def get_count(cls, obj, attr):
        key = cls.get_key_for_count(obj, attr)
        conn = RedisClient.get_connection()

        # use pipeline
        with conn.pipeline() as pipe:
            pipe.get(key)
            pipe.ttl(key)
            value, ttl = pipe.execute()

        if value is None:

            obj.refresh_from_db()
            db_value = getattr(obj, attr, 0)


            conn.setex(key, cache_constants.REDIS_KEY_EXPIRE_TIME, db_value)
            return db_value


        if 0 < ttl < 3600:
            conn.expire(key, cache_constants.REDIS_KEY_EXPIRE_TIME)

        return int(value)

    @classmethod
    def refresh_count(cls, obj, attr):

        key = cls.get_key_for_count(obj, attr)
        conn = RedisClient.get_connection()
        obj.refresh_from_db()
        conn.setex(key, cache_constants.REDIS_KEY_EXPIRE_TIME, getattr(obj, attr))
        return getattr(obj, attr)