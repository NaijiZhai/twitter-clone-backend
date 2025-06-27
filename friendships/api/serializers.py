from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.api.serializers import UserSerializerForFriendship
from friendships.models import Friendship
from friendships.services import FriendshipServices


class FollowerSerializer(serializers.Serializer):
    user = UserSerializerForFriendship(source='from_user', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    has_followed = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ('user', 'created_at', 'has_followed')

    def get_has_followed(self, obj):
        request = self.context.get('request')
        if request.user.is_anonymous:
            return False
        return FriendshipServices.has_followed(request.user, obj.from_user)


class FollowingSerializer(serializers.Serializer):
    user = UserSerializerForFriendship(source='to_user', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    has_followed = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ('user', 'created_at', 'has_followed')

    # whether this current request.user has followed the user in the following list.
    def get_has_followed(self, obj):
        request = self.context.get('request')
        if request.user.is_anonymous:
            return False
        return FriendshipServices.has_followed(request.user, obj.to_user)


class FriendSerializerForCreate(serializers.Serializer):
    from_user_id = serializers.IntegerField()
    to_user_id = serializers.IntegerField()
    created_at = serializers.DateTimeField(read_only=True)

    def validate(self, data):
        if data['from_user_id'] == data['to_user_id']:
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
