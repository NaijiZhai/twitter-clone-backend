from rest_framework import serializers

from newsfeeds.models import NewsFeed
from tweets.api.serializers import TweetSerializer


class NewsFeedSerializer(serializers.ModelSerializer):
    tweet = TweetSerializer(source='cached_tweet', read_only=True)

    class Meta:
        model = NewsFeed
        fields = ('id', 'created_at', 'tweet')
