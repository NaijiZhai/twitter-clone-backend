from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from likes.api.serializers import LikeSerializerForCreate, LikeSerializer
from likes.models import Like
from utils.decorator import require_all_params


class LikeViewSet(GenericViewSet):
    queryset = Like.objects.all()
    serializer_class = LikeSerializerForCreate
    permission_classes = [IsAuthenticated, ]

    @require_all_params(request_attr='data', params=['content_type', 'content_id'])
    def create(self, request, *args, **kwargs):
        serializer = LikeSerializerForCreate(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)
        like = serializer.save()
        return Response({'success': True, 'data': LikeSerializer(like).data}, status=201)

    @require_all_params(params=['content_type', 'content_id'], request_attr='query_params')
    @action(methods=['delete'], detail=False)
    def delete(self, request, **kwargs):
        query_params = request.query_params
        is_deleted, _ = Like.objects.filter(user=request.user, content_type=query_params['content_type'],
                                            content_id=query_params['content_id']).delete()
        if not is_deleted:
            return Response({'message': 'like does not exit'}, status=400)
        return Response({'success': True, 'delete': is_deleted}, status=204)
