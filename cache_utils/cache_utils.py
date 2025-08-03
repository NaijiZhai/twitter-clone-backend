from django.conf import settings
from django.core.cache import caches
from django.core.serializers import deserialize

from cache_utils.redis_serializer import RedisSerializer
from utils.micro_second_json_encoder import MicrosecondEncoder

cache = caches['testing'] if settings.TESTING else caches['default']


class CacheUtils:

    @classmethod
    def get_key(cls, model, id):
        return f"{model.__name__}:{id}"

    @classmethod
    def get_object_in_cache(cls, model, id, ):
        key = cls.get_key(model, id)
        obj = cache.get(key)

        #not right here, the obj returned will never be None
        #obj = RedisSerializer.deserialize(obj)
        if obj:
            obj = RedisSerializer.deserialize(obj)
            return obj

        obj = model.objects.get(id=id)
        if obj and cache:
            cache.set(key, RedisSerializer.serialize(obj))
        return obj

    @classmethod
    def set_object_in_cache(cls, model, obj):
        key = cls.get_key(model, obj.id)
        obj = RedisSerializer.serialize(obj)
        cache.set(key, obj)

    @classmethod
    def invalidate_cache(cls, model, id):
        key = cls.get_key(model, id)
        cache.delete(key)

    @classmethod
    def get_many(cls, keys):
        return cache.get_many(keys)

