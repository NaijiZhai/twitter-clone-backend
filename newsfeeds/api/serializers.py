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
        """自定义ID字段的序列化方法"""
        if hasattr(instance, 'is_pull_mode') and instance.is_pull_mode:
            # 对于pull模式的对象，直接返回字符串ID
            return str(instance.id)
        else:
            # 对于正常的NewsFeed对象，返回整数ID
            return instance.id

    def to_representation(self, instance):
        """
        自定义序列化以处理pull模式的伪对象
        """
        data = super().to_representation(instance)

        # 确保tweet数据正确序列化
        if hasattr(instance, 'cached_tweet') and instance.cached_tweet:
            tweet_serializer = TweetSerializer(instance.cached_tweet, context=self.context)
            data['tweet'] = tweet_serializer.data
        elif hasattr(instance, 'tweet') and instance.tweet:
            tweet_serializer = TweetSerializer(instance.tweet, context=self.context)
            data['tweet'] = tweet_serializer.data

        # 对于pull模式的数据，可以添加特殊标记
        if hasattr(instance, 'is_pull_mode') and instance.is_pull_mode:
            data['source'] = 'pull'
        else:
            data['source'] = 'push'

        return data