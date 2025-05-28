from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.api.serializers import UserSerializerForFriendship, UserSerializer
from friendships.models import Friendship


class FollowerSerializer(serializers.Serializer):
    user = UserSerializerForFriendship(source='from_user', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Friendship
        fields  = ('user', 'created_at')


class FollowingSerializer(serializers.Serializer):
    user = UserSerializerForFriendship(source='to_user', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Friendship
        fields  = ('user', 'created_at')





