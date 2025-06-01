from rest_framework import serializers

from accounts.api.serializers import UserSerializer
from comments.models import Comment
from tweets.api.serializers import TweetSerializer


class CommentSerializerForCreate(serializers.Serializer):
    user = UserSerializer(read_only=True)
    tweet = TweetSerializer(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    content = serializers.CharField(max_length=140)
    updated_at = serializers.DateTimeField(read_only=True)

    def validate(self, data):
        if not self.context['request'].user.is_authenticated():
            raise serializers.ValidationError('You need to log in first')
        return data

    def create(self, validated_data):
        return Comment.objects.create(**validated_data)




