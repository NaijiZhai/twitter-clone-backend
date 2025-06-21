from rest_framework import serializers

from accounts.api.serializers import UserSerializer, UserSerializerForComment
from comments.models import Comment
from likes.services import LikeService
from tweets.models import Tweet


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializerForComment()
    has_liked = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()


    class Meta:
        model = Comment
        fields = 'id', 'tweet_id', 'user', 'content', 'created_at','like_count','has_liked'

    def get_has_liked(self, obj):
        return LikeService.has_user_liked(self.context['request'].user, obj)

    def get_like_count(self, obj):
        return obj.like_set.count()


class CommentSerializerForCreate(serializers.ModelSerializer):
    tweet_id = serializers.IntegerField()
    user_id = serializers.IntegerField()

    class Meta:
        model = Comment
        fields = ('user_id', 'tweet_id', 'content')

    def validate(self, data):
        if not Tweet.objects.filter(id=data.get('tweet_id')):
            raise serializers.ValidationError({'message': 'tweet does not exist'})
        return data

    def create(self, validated_data):
        print(validated_data)
        return Comment.objects.create(**validated_data)


class CommentSerializerForUpdate(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('content',)

    def update(self, instance, validated_data):
        instance.content = validated_data['content']
        instance.save()
        return instance


class CommentSerializerForList(serializers.ModelSerializer):

    has_liked = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ('content', 'tweet_id', 'user_id','has_liked', 'like_count')
        ordering = ('-created_at',)

    def get_has_liked(self, obj):
        return LikeService.has_user_liked(self.context['request'].user, obj)
    def get_like_count(self, obj):
        return obj.like_set.count()