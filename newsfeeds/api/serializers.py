from rest_framework import serializers
from newsfeeds.models import NewsFeed
from tweets.api.serializers import TweetSerializer


class NewsFeedSerializer(serializers.ModelSerializer):
    tweet = TweetSerializer(source='cached_tweet', read_only=True)
    id = serializers.SerializerMethodField()  # 自定义ID字段处理

    class Meta:
        model = NewsFeed
        fields = ('id', 'created_at', 'tweet')

    def get_id(self, instance):
        """Custom serialization method for ID field"""
        if hasattr(instance, 'is_pull_mode') and instance.is_pull_mode:
            #
            return str(instance.id)
        else:
            return instance.id

    # def to_representation(self, instance):
    #     """
    #     自定义序列化以处理pull模式的伪对象
    #     """
    #     data = super().to_representation(instance)
    #
    #     if hasattr(instance, 'tweet') and instance.tweet:
    #         tweet_serializer = TweetSerializer(instance.tweet, context=self.context)
    #         data['tweet'] = tweet_serializer.data
    #
    #     # mark as pull
    #     if hasattr(instance, 'is_pull_mode') and instance.is_pull_mode:
    #         data['source'] = 'pull'
    #     else:
    #         data['source'] = 'push'
    #
    #     return data