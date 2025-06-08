from openai import OpenAI
from rest_framework import serializers

from accounts.api.serializers import UserSerializerForTweetResponse, UserSerializer
from comments.api.serializers import CommentSerializer
from tweets.models import Tweet


class TweetSerializerForCreate(serializers.ModelSerializer):
    content = serializers.CharField(max_length=140, min_length=6)

    class Meta:
        model = Tweet
        fields = ('content',)

    def validate(self, data):
        content = data['content']
        response = OpenAI(api_key=('sk-proj-40fHvTGAz_JNcwsoiWbcl9Bx1YM0u2yn6jaLQZ-jmVE9sfFt74k9'
                                   'JSMUgBXawbFdiufGG5pVr6T3BlbkFJ-oEJBpwg700nkbnJqlSjacXaPd9hmz5Uv6a51dK-C_j380bTrkXhaJc8AjXAjeh0IhXbUjjBMA')).moderations.create(
            input=content,
        )
        if response.results[0].flagged:
            raise serializers.ValidationError('Harmful content！')
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        content = validated_data['content']
        tweet = Tweet.objects.create(user=user, content=content)
        return tweet


class TweetSerializer(serializers.ModelSerializer):
    user = UserSerializerForTweetResponse(read_only=True)

    class Meta:
        model = Tweet
        fields = ('id', 'user', 'content', 'created_at')


class TweetSerializerWithComments(serializers.ModelSerializer):
    user = UserSerializer()
    comments = serializers.SerializerMethodField()


    class Meta:
        model = Tweet
        fields = ('id', 'user', 'content', 'created_at', 'comments')

    def get_comments(self, obj):
        limit = self.context.get('limit', None)
        comments = obj.comment_set.all().order_by('-created_at')
        print(limit)
        if limit is not None:
            comments = comments[:limit+1]
        return CommentSerializer(comments, many=True).data
