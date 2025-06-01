from httplib2.auth import params
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from friendships.api.serializers import FollowerSerializer, FollowingSerializer, FriendSerializerForCreate
from rest_framework.request import Request
from accounts.api.serializers import UserSerializerForTweetResponse
from friendships.models import Friendship
from utils.auth import CsrfExemptSessionAuthentication


class FriendshipViewSet(viewsets.GenericViewSet):
    # 'FriendshipViewSet' should either include a `queryset` attribute, or override the `get_queryset()` method.
    queryset = Friendship.objects.all()
    serializer_class = FriendSerializerForCreate
    authentication_classes = [CsrfExemptSessionAuthentication]

    def get_permissions(self):
        if self.action == 'create' or self.action == 'destroy':
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        params = self.request.query_params
        if 'from_user_id' in params and 'to_user_id' in params:
            return Friendship.objects.none()
        elif 'from_user_id' in params:
            return Friendship.objects.filter(from_user_id=params['from_user_id']).order_by('-created_at')
        elif 'to_user_id' in params:
            return Friendship.objects.filter(to_user_id=params['to_user_id']).order_by('-created_at')
        return Friendship.objects.none()

    def get_serializer_class(self):
        params = self.request.query_params
        if self.action == 'create':
            return FriendSerializerForCreate
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

    def create(self, request):
        if not ('to_user_id' in request.data and 'from_user_id' in request.data):
            return Response('to_user_id and from_user_id are both needed', status=400)
        if Friendship.objects.filter(from_user_id=request.data['from_user_id'],
                                     to_user_id=request.data['to_user_id']).exists():
            return Response({'success': True, 'duplicate': True}, status=200)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response({'success': True, 'duplicate': False, 'data': serializer.data}, status=201)

    @action(methods=['delete'], detail=False, url_path='remove')
    def delete(self, request, **kwargs):
        query_params = request.query_params
        print(query_params)
        if not ('to_user_id' in query_params and 'from_user_id' in query_params):
            return Response('to_user_id and from_user_id are both needed', status=400)
        is_deleted, _ = Friendship.objects.filter(from_user_id=query_params['from_user_id'],
                                                  to_user_id=query_params['to_user_id']).delete()
        if not is_deleted:
            return Response({'message': 'friendship does not exit'}, status=400)
        return Response({'success': True, 'delete': is_deleted}, status=204)b
