from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.api.serializers import UserSerializerForTweetResponse, UserSerializer
from friendships.models import Friendship


class FollowerSerializer(serializers.Serializer):
    user = UserSerializer(source='user', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Friendship
        fields  = '__all__'





