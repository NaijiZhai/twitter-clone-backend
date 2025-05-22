from rest_framework import serializers
from openai import OpenAI

from accounts.api.serializers import UserSerializer, UserSerializerForTweetResponse
from tweets.models import Tweet


class TweetCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tweet


class TweetSerializer(serializers.ModelSerializer):
    user = UserSerializerForTweetResponse(read_only=True)
    class Meta:
        model = Tweet
        fields = ('id', 'user', 'content', 'created_at')
