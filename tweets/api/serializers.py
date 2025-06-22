from openai import OpenAI
from rest_framework import serializers

from accounts.api.serializers import UserSerializerForTweetResponse, UserSerializer, UserSerializerWithProfile
from comments.api.serializers import CommentSerializer
from likes.api.serializers import LikeSerializer
from likes.services import LikeService
from tweets.models import Tweet
from tweets.services import TweetService


class TweetSerializerForCreate(serializers.ModelSerializer):
    content = serializers.CharField(max_length=140, min_length=6)
    photos = serializers.ListField(child=serializers.FileField(), required=False,allow_empty=True)

    class Meta:
        model = Tweet
        fields = ('content','photos')

    def validate(self, data):
        content = data['content']
        response = OpenAI(api_key=('sk-proj-40fHvTGAz_JNcwsoiWbcl9Bx1YM0u2yn6jaLQZ-jmVE9sfFt74k9'
                                   'JSMUgBXawbFdiufGG5pVr6T3BlbkFJ-oEJBpwg700nkbnJqlSjacXaPd9hmz5Uv6a51dK-C_j3'
                                   '80bTrkXhaJc8AjXAjeh0IhXbUjjBMA')).moderations.create(
            input=content,
        )
        if response.results[0].flagged:
            raise serializers.ValidationError('Harmful content！')

        photos = data.get('photos',[])
        if len(photos) > 4:
            raise serializers.ValidationError('Too many photos')

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        content = validated_data['content']
        tweet = Tweet.objects.create(user=user, content=content)
        if 'photos' in validated_data:
            TweetService.create_photos(tweet, validated_data['photos'])
        return tweet


class TweetSerializer(serializers.ModelSerializer):
    user = UserSerializerForTweetResponse(read_only=True)
    has_liked = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    photo_urls = serializers.SerializerMethodField()

    class Meta:
        model = Tweet
        fields = ('id',
                  'user',
                  'content',
                  'created_at',
                  'comment_count',
                  'like_count',
                  'has_liked',
                  'photo_urls')

    def get_has_liked(self, obj):
        request = self.context.get('request')
        if request is None:
            return False
        return LikeService.has_user_liked(request.user, obj)

    def get_comment_count(self, obj):
        return obj.comment_set.count()

    def get_like_count(self, obj):
        return obj.like_set.count()

    def get_photo_urls(self,obj):
        photo_urls = []
        for photo in obj.tweetphoto_set.all():
            photo_urls.append(photo.file.url)
        return photo_urls


class TweetSerializerWithDetails(TweetSerializer):
    user = UserSerializerWithProfile()
    comments = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()

    class Meta:
        model = Tweet
        fields = ('id', 'user', 'content', 'created_at', 'comments', 'likes', 'like_count', 'comment_count',
                  'has_liked','photo_urls')

    def get_comments(self, obj):
        limit = self.context.get('limit', None)
        comments = obj.comment_set.all().order_by('-created_at')
        if limit is not None:
            comments = comments[:limit]
        return CommentSerializer(comments, context=self.context, many=True).data

    def get_likes(self, obj):
        return LikeSerializer(obj.like_set.all(), many=True).data
