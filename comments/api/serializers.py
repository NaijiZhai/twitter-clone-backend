from rest_framework import serializers

from accounts.api.serializers import UserSerializer
from comments.models import Comment
from tweets.models import Tweet


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Comment
        fields = 'id', 'tweet_id', 'user', 'content', 'created_at'


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

    class Meta:
        model = Comment
        fields = ('content', 'tweet_id', 'user_id')
        ordering = ('-created_at',)
