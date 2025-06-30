from django.conf import settings
from django.core.cache import caches

cache = caches['testing'] if settings.TESTING else caches['default']


class CacheUtils:

    @classmethod
    def get_key(cls, model, id):
        return f"{model.__name__}:{id}"

    @classmethod
    def get_object_in_cache(cls, model, id, id_for_model = True):
        key = cls.get_key(model, id)
        obj = cache.get(key)
        if obj:
            return obj
        obj = model.objects.get(id=id)
        if obj and cache:
            cache.set(key, obj)
        return obj

    @classmethod
    def invalidate_cache(cls, model, id):
        key = cls.get_key(model, id)
        cache.delete(key)


