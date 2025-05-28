from httplib2.auth import params
from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from friendships.api.serializers import FollowerSerializer, FollowingSerializer
from rest_framework.request import Request
from accounts.api.serializers import UserSerializerForTweetResponse
from friendships.models import Friendship


class FriendshipViewSet(viewsets.GenericViewSet):
    # 'FriendshipViewSet' should either include a `queryset` attribute, or override the `get_queryset()` method.
    queryset = Friendship.objects.all()

    def get_queryset(self):
        params = self.request.query_params
        if 'from_user_id' in params:
            return Friendship.objects.filter(from_user_id=params['from_user_id']).order_by('-created_at')
        if 'to_user_id' in params:
            return Friendship.objects.filter(to_user_id=params['to_user_id']).order_by('-created_at')
        return Friendship.objects.none()

    def get_serializer_class(self):
        params = self.request.query_params
        if 'from_user_id' in params:
            return FollowingSerializer
        if 'to_user_id' in params:
            return FollowerSerializer
        return FollowingSerializer

    def list(self, request):
        if not ('to_user_id' in request.query_params or 'from_user_id' in request.query_params):
            return Response('either to_user_id or from_user_id is needed', status=400)
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        key = 'followings' if 'from_user_id' in request.query_params else 'followers'
        return Response({
            key: serializer.data,
        }, status=200)
