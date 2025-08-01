import json

from django.conf import settings
from django.core.cache import cache, caches

from cache_utils import cache_constants
from cache_utils.cache_utils import CacheUtils
from cache_utils.redis_client import RedisClient
from cache_utils.redis_serializer import RedisSerializer
cache = caches['testing'] if settings.TESTING else caches['default']

class RedisHelper:

    @classmethod
    def _serialize_newsfeed_item(cls, obj):
        """
        use django serializer to serialize newsfeed item
        """
        return RedisSerializer.serialize(obj)

    @classmethod
    def _deserialize_newsfeed_item(cls, item_bytes):
        """
        use django serializer to deserialize newsfeed item
        """
        return RedisSerializer.deserialize(item_bytes)

    @classmethod
    def get_from_redis_ordered(cls, key, user_id, model=None):
        """
        get objects from redis ordered cache
        """
        conn = RedisClient.get_connection()

        if conn.exists(key):
            cached_items = conn.lrange(key, 0, -1)
            if not cached_items:
                return cls._rebuild_ordered_cache(key, user_id, model)


            objects = []
            missed_items = []

            for item_bytes in cached_items:
                item_data = cls._deserialize_newsfeed_item(item_bytes)

                if type(item_data.id) == int:
                    objects.append(item_data)
                else:
                    try:
                        from tweets.models import Tweet
                        tweet = Tweet.objects.select_related('user').get(id=item_data['tweet_id'])
                        pseudo_newsfeed = cls._create_pseudo_newsfeed(tweet, user_id)
                        objects.append(pseudo_newsfeed)
                    except Tweet.DoesNotExist:
                        missed_items.append(item_data)

            # 如果有缺失的项，重建缓存
            if missed_items:
                return cls._rebuild_ordered_cache(key, user_id, model)

            return objects

        # 缓存不存在，重建
        return cls._rebuild_ordered_cache(key, user_id, model)

    @classmethod
    def _load_objects_to_cache_ordered(cls, key, queryset, model=None):
        """
        有序加载对象到缓存
        """
        conn = RedisClient.get_connection()
        objects = []

        # 获取实际对象以获取时间戳信息
        db_objects = list(
            model.objects.filter(id__in=queryset).select_related('tweet')[:cache_constants.REDIS_LIST_LIMIT_LENGTH])

        # 按时间排序
        db_objects.sort(key=lambda x: (x.created_at, x.id), reverse=True)

        cache_items = [cls._serialize_newsfeed_item(obj) for obj in db_objects]

        if cache_items:
            conn.rpush(key, *cache_items)
            conn.expire(key, cache_constants.REDIS_KEY_EXPIRE_TIME)

    @classmethod
    def invalidate_cache(cls, key):
        conn = RedisClient.get_connection()
        conn.delete(key)

    @classmethod
    def refresh_ordered_cache(cls, key, user_id, model):
        """
        refresh cache for newsfeeds ordered by time
        """
        cls.invalidate_cache(key)
        return cls.get_from_redis_ordered(key, user_id, model)

    @classmethod
    def _rebuild_ordered_cache(cls, key, user_id, model):
        """
        重建有序缓存
        """
        # 使用混合模式获取数据
        from newsfeeds.services import NewsFeedService
        newsfeeds = NewsFeedService.get_newsfeed_hybrid(
            user_id=user_id,
            count=cache_constants.REDIS_LIST_LIMIT_LENGTH
        )

        # 构建缓存数据
        conn = RedisClient.get_connection()
        conn.delete(key)  # 清除旧缓存

        if newsfeeds:
            cache_items = [cls._serialize_newsfeed_item(nf) for nf in newsfeeds]
            conn.rpush(key, *cache_items)
            conn.expire(key, cache_constants.REDIS_KEY_EXPIRE_TIME)

        return newsfeeds

    @classmethod
    def _create_pseudo_newsfeed(cls, tweet, user_id):
        """
        create a pseudo newsfeed object for tweets that don't have a corresponding newsfeed record in the database.
        """
        return type('NewsFeed', (), {
            'id': f"pull_{tweet.id}_{user_id}",
            'tweet': tweet,
            'tweet_id': tweet.id,
            'user_id': user_id,
            'created_at': tweet.created_at,
            'cached_tweet': tweet,
            'is_pull_mode': True  # Add a flag to identify pull mode objects
        })()

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
            queryset = model.objects.filter(user=obj.user).order_by('-created_at')
            cls._load_objects_to_cache(key, queryset.values_list('id', flat=True), model)
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
    def get_objs_from_redis(cls, key, user_id, model=None):
        conn = RedisClient.get_connection()
        objects = []
        pseudo_objs = {}
        if conn.exists(key):
            obj_list = conn.lrange(key, 0, -1)
            for obj_id in obj_list:


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