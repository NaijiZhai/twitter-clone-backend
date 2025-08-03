import json
from utils.micro_second_json_encoder import MicrosecondEncoder


class RedisSerializer:

    @classmethod
    def serialize(cls, obj):
        #
        if hasattr(obj, 'is_pull_mode') and obj.is_pull_mode:
            return cls._serialize_pseudo_newsfeed(obj)
        else:
            # use django serializer
            from django.core import serializers
            return serializers.serialize('json', [obj], cls=MicrosecondEncoder)

    @classmethod
    def _serialize_pseudo_newsfeed(cls, obj):
        """serialize pseudo newsfeed"""
        data = {
            'model': 'newsfeeds.newsfeed',
            'pk': str(obj.id),
            'fields': {
                'user': obj.user_id,
                'tweet': obj.tweet_id,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'insert_tag': getattr(obj, 'insert_tag', ''),
                'is_pull_mode': True,  # mark pseudo newsfeed
            }
        }
        return json.dumps([data], cls=MicrosecondEncoder)

    @classmethod
    def deserialize(cls, json_string):
        if not isinstance(json_string, (str, bytes)):
            if hasattr(json_string, '__class__'):
                return json_string

        data = json.loads(json_string)[0]

        # check if it is pseudo newsfeed
        if data.get('fields', {}).get('is_pull_mode'):
            return cls._deserialize_pseudo_newsfeed(data)
        else:
            from django.core import serializers
            return list(serializers.deserialize('json', json_string))[0].object

    @classmethod
    def _deserialize_pseudo_newsfeed(cls, data):
        """deserialize pseudo newsfeed"""
        fields = data['fields']

        # rebuild pseudo_newsfeed
        tweet = None
        if fields.get('tweet'):
            try:
                from tweets.models import Tweet
                tweet = Tweet.objects.select_related('user').get(id=fields['tweet'])
            except Tweet.DoesNotExist:
                pass

        # rebuild pseudo_newsfeed
        if tweet:
            from cache_utils.redis_helper import RedisHelper
            return RedisHelper.create_pseudo_newsfeed(tweet, fields['user'])
        else:
            #return null newsfeed
            from newsfeeds.models import NewsFeed
            from datetime import datetime

            pseudo = NewsFeed()
            pseudo.id = data['pk']
            pseudo.user_id = fields['user']
            pseudo.tweet_id = fields['tweet']
            pseudo.tweet = None
            pseudo.created_at = datetime.fromisoformat(fields['created_at']) if fields['created_at'] else None
            pseudo.insert_tag = fields.get('insert_tag', '')
            pseudo.is_pull_mode = True

            pseudo._state.adding = False
            pseudo._state.db = None

            return pseudo
