from rest_framework.serializers import ModelSerializer

from accounts.api.serializers import UserSerializer, UserSerializerForLike
from comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from likes.models import Like
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from tweets.models import Tweet


class LikeSerializer(serializers.ModelSerializer):
    user = UserSerializerForLike()

    class Meta:
        model = Like
        fields = ('user', 'created_at')


class LikeSerializerForCreate(serializers.ModelSerializer):
    content_type = serializers.ChoiceField(choices=['comment', 'tweet'])
    content_id = serializers.IntegerField()

    class Meta:
        model = Like
        fields = ('content_type', 'content_id')

    def _get_model_class(self, data):
        if data['content_type'] == 'comment':
            return Comment
        if data['content_type'] == 'tweet':
            return Tweet
        return None

    def validate(self, data):
        model_class = self._get_model_class(data)
        if model_class is None:
            raise ValidationError({'content_type': 'Content type does not exist'})
        liked_object = model_class.objects.filter(id=data['content_id']).first()
        if liked_object is None:
            raise ValidationError({'content_id': 'Object does not exist'})
        return data

    def get_or_create(self):
        validated_data = self.validated_data
        model_class = self._get_model_class(validated_data)
        return Like.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(model_class),
            content_id=validated_data['content_id'],
            user=self.context['request'].user,
        )


class LikeSerializerForDelete(ModelSerializer):
    content_type = serializers.ChoiceField(choices=['comment', 'tweet'])
    content_id = serializers.IntegerField()

    class Meta:
        model = Like
        fields = 'content_type', 'content_id'

    def _get_model_class(self, data):
        if data['content_type'] == 'comment':
            return Comment
        if data['content_type'] == 'tweet':
            return Tweet
        return None

    def validate(self, data):
        model_class = self._get_model_class(data)
        if model_class is None:
            raise ValidationError({'content_type': 'Content type does not exist'})
        liked_object = model_class.objects.filter(id=data['content_id']).first()
        if liked_object is None:
            raise ValidationError({'content_id': 'Object does not exist'})
        return data

    def delete(self, validated_data):
        model_class = self._get_model_class(validated_data)
        return Like.objects.filter(
            content_type=ContentType.objects.get_for_model(model_class),
            content_id=validated_data['content_id'],
            user=self.context['request'].user,
        ).delete()

