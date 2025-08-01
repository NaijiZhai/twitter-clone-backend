from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.api.serializers import UserSerializerForFriendship
from friendships.models import Friendship
from friendships.services import FriendshipServices



class FollowingSetMixin:

    @property
    def following_user_id_set(self:serializers.ModelSerializer):
        if self.context['request'].user.is_anonymous:
            return set()
        if hasattr(self, '_cached_following_user_id_set'):
            return self._cached_following_user_id_set
        user_id_set = FriendshipServices.get_following_id_set(self.context['request'].user.id)
        setattr(self, '_cached_following_user_id_set', user_id_set)
        return user_id_set



class FollowerSerializer(serializers.Serializer, FollowingSetMixin):
    user = UserSerializerForFriendship(source='cached_from_user', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    has_followed = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ('user', 'created_at', 'has_followed')

    def get_has_followed(self, obj):
        return obj.from_user_id in self.following_user_id_set


class FollowingSerializer(serializers.Serializer, FollowingSetMixin):
    user = UserSerializerForFriendship(source='cached_to_user', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    has_followed = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ('user', 'created_at', 'has_followed')

    # whether this current request.user has followed the user in the following list.
    def get_has_followed(self, obj):
        return obj.to_user_id in self.following_user_id_set


class FriendSerializerForCreate(serializers.Serializer):
    to_user_id = serializers.IntegerField()
    created_at = serializers.DateTimeField(read_only=True)

    def validate(self, data):
        data['from_user_id'] = self.context['request'].user.id
        if  data['from_user_id'] == data['to_user_id']:
            raise serializers.ValidationError('You can\'t follow yourself')
        if not User.objects.filter(id=data['from_user_id']).exists():
            raise serializers.ValidationError('From user does not exist')
        if not User.objects.filter(id=data['to_user_id']).exists():
            raise serializers.ValidationError('To user does not exist')
        return data

    def create(self, validated_data):
        from_user = User.objects.get(id=validated_data['from_user_id'])
        to_user = User.objects.get(id=validated_data['to_user_id'])
        return Friendship.objects.create(from_user=from_user, to_user=to_user)
