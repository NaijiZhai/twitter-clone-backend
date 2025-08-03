import json

from django.conf import settings
from django.core.cache import cache, caches

from cache_utils import cache_constants
from cache_utils.cache_constants import REDIS_LIST_LIMIT_LENGTH, NEWSFEED_USER_PATTERN
from cache_utils.cache_utils import CacheUtils
from cache_utils.redis_client import RedisClient
from cache_utils.redis_serializer import RedisSerializer
from newsfeeds.tasks import sync_newsfeed_cache_task

cache = caches['testing'] if settings.TESTING else caches['default']

class RedisHelper:

    @classmethod
    def load_newsfeeds_to_cache_ordered(cls, key, cache_items):
        """
        """
        conn = RedisClient.get_connection()
        if cache_items:
            cache_items = [RedisSerializer.serialize(item) for item in cache_items]
            conn.rpush(key, *cache_items)
            conn.expire(key, cache_constants.REDIS_KEY_EXPIRE_TIME)

    @classmethod
    def invalidate_cache(cls, key):
        conn = RedisClient.get_connection()
        conn.delete(key)


    @classmethod
    def create_pseudo_newsfeed(cls, tweet, user_id):
        from newsfeeds.models import NewsFeed

        # real newsfeed but do not save in db
        pseudo = NewsFeed()
        pseudo.id = f"pull_{tweet.id}_{user_id}"
        pseudo.tweet = tweet
        pseudo.tweet_id = tweet.id
        pseudo.user_id = user_id
        pseudo.created_at = tweet.created_at
        pseudo.is_pull_mode = True
        pseudo.insert_tag = ''  # default value

        # mark this as pseduo obj so do not store in db
        pseudo._state.adding = False
        pseudo._state.db = None

        return pseudo

    @classmethod
    def push_obj_id(cls, key, obj, model):
        conn = RedisClient.get_connection()
        if not conn.exists(key):
            queryset = model.objects.filter(user=obj.user).order_by('-created_at').values_list('id', flat=True)
            cls._load_objects_to_cache(key, queryset, model)
            return
        conn.lpush(key, obj.id)
        conn.ltrim(key, 0, cache_constants.REDIS_LIST_LIMIT_LENGTH - 1)

    @classmethod
    def push_obj(cls, key, obj, model):
        conn = RedisClient.get_connection()
        if not conn.exists(key):
            sync_newsfeed_cache_task.delay(obj.user_id)
            return
        conn.lpush(key, RedisSerializer.serialize(obj))
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
    def get_newsfeeds_from_redis(cls, key, user_id, model=None):
        conn = RedisClient.get_connection()
        if not conn.exists(key):
            from newsfeeds.services import NewsFeedService
            from django.utils import timezone

            # use current timestamp
            now = timezone.now()
            newsfeeds = NewsFeedService._get_newsfeeds_from_db_and_pull(
                user_id, None, REDIS_LIST_LIMIT_LENGTH, created_at_lt=now, created_at_gt=None
            )
            cls.load_newsfeeds_to_cache_ordered(NEWSFEED_USER_PATTERN.format(user_id=user_id), newsfeeds)

            return newsfeeds

        obj_list = conn.lrange(key, 0, -1)
        objects = [RedisSerializer.deserialize(obj) for obj in obj_list]
        return objects


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
    def get_key_for_count(cls, obj, attr):
        return f"{obj.__class__.__name__}.{attr}:{obj.id}"

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

    @classmethod
    def get_last_obj_in_cache(cls, key):
        conn = RedisClient.get_connection()
        if conn.exists(key):
            obj = conn.lindex(key, -1)
            return json.loads(obj)[0]
        return None