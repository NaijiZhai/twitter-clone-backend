from django.contrib.auth.models import User
from rest_framework.decorators import action
from rest_framework import viewsets, permissions
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from friendships.api.serializers import FollowerSerializer

from accounts.api.serializers import UserSerializerForTweetResponse
from friendships.models import Friendship


class FriendshipViewSet(viewsets.GenericViewSet):


    # 'FriendshipViewSet' should either include a `queryset` attribute, or override the `get_queryset()` method.
    queryset = User.objects.all()

    @action(methods = ['get'], detail = True, permission_classes = [AllowAny])
    def followers(self, request,pk=None):
        user = self.get_object()
        friendships = Friendship.objects.filter(to_user=user).order_by('-created_at')
        followers = FollowerSerializer(friendships, many=True).data
        return Response({
            'followers': followers
        }, status = 200)

    @action(methods = ['get'], detail = True, permission_classes = [permissions.IsAuthenticated])
    def following(self,request, pk = None):
        user = self.get_object()


