from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from likes.api.serializers import LikeSerializerForCreate, LikeSerializer, LikeSerializerForDelete
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

    @require_all_params(params=['content_type', 'content_id'], request_attr='data')
    @action(methods=['delete'], detail=False)
    def delete(self, request, **kwargs):
        data = request.data
        serializer = LikeSerializerForDelete(data=data, context={'request': request})
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=400)
        is_deleted, _= serializer.delete(serializer.validated_data)
        return Response({'success': True, 'delete': is_deleted}, status=200)
