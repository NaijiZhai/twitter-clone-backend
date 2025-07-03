from utils.micro_second_json_encoder import MicrosecondEncoder
from django.core import serializers

class RedisSerializer:

    @classmethod
    def serialize(cls, obj):
        return serializers.serialize('json', [obj], cls=MicrosecondEncoder)

    @classmethod
    def deserialize(cls, json_string):
        # use .object for DeserializedObject, use list since it is a generator
        return list(serializers.deserialize('json', json_string))[0].object
