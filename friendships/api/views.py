from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from friendships.api.serializers import FollowerSerializer, FollowingSerializer, FriendSerializerForCreate
from friendships.models import Friendship
from newsfeeds.services import NewsFeedService
from utils.auth import CsrfExemptSessionAuthentication
from utils.decorator import require_all_params, require_any_params
from utils.pagination import CustomPagination
from utils.rate_limiter import rate_limit


class FriendshipViewSet(viewsets.GenericViewSet):
    # 'FriendshipViewSet' should either include a `queryset` attribute, or override the `get_queryset()` method.
    queryset = Friendship.objects.all()
    serializer_class = FriendSerializerForCreate
    authentication_classes = [CsrfExemptSessionAuthentication]
    pagination_class = CustomPagination

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

    @require_any_params(params=['from_user_id', 'to_user_id',])
    @rate_limit('3/s')
    def list(self, request):
        page = self.paginate_queryset(self.get_queryset())
        serializer = self.get_serializer(page, many=True)
        key = 'followings' if 'from_user_id' in request.query_params else 'followers'
        return self.get_paginated_response({key: serializer.data})

    @require_all_params(params=['to_user_id'], request_attr='data')
    @rate_limit('3/s')
    def create(self, request):
        if Friendship.objects.filter(from_user_id=request.user.id,
                                     to_user_id=request.data['to_user_id']).exists():
            return Response({'success': True, 'duplicate': True}, status=200)
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        NewsFeedService.inject_newsfeed(from_user_id=request.user.id, to_user_id=request.data['to_user_id'])
        return Response({'success': True, 'duplicate': False, 'data': serializer.data}, status=201)

    @require_all_params(params=['to_user_id'])
    @action(methods=['delete'], detail=False)
    @rate_limit('3/s')
    def delete(self, request, **kwargs):
        from_user_id = request.user.id
        to_user_id = request.query_params['to_user_id']

        is_deleted, _ = Friendship.objects.filter(
            from_user_id=from_user_id,
            to_user_id=to_user_id
        ).delete()

        if not is_deleted:
            return Response({'message': 'friendship does not exist'}, status=400)

        NewsFeedService.remove_newsfeed(from_user=from_user_id, to_user=to_user_id)
        return Response({'success': True, 'deleted': is_deleted}, status=204)