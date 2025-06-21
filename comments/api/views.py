from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

import notification
from utils.permissions import IsOwner
from comments.api.serializers import CommentSerializerForCreate, CommentSerializer, CommentSerializerForUpdate, \
    CommentSerializerForList
from comments.models import Comment
from utils.decorator import require_all_params


# Create your views here.
class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializerForCreate
    filterset_fields = ('tweet_id',)

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        if self.action in ['destroy', 'update']:
            return [IsAuthenticated(), IsOwner()]
        return [AllowAny()]

    @require_all_params(params=['tweet_id'])
    def list(self, request, *args, **kwargs):
        comments = self.filter_queryset(self.get_queryset())
        serializer = CommentSerializerForList(comments, context={'request':request}, many=True)
        return Response({'comments':serializer.data}, status=200)




    def create(self, request, *args, **kwargs):

        data = {
            'user_id': request.user.id,
            'tweet_id': request.data.get('tweet_id'),
            'content': request.data.get('content'),
        }
        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            return Response({'message': 'error', 'errors': serializer.errors}, status=400)
        comment = serializer.save()
        notification.services.NotificationService.send_comment_notification(comment)
        return Response(
            CommentSerializer(comment, context={'request':request}).data,
            status=201
        )

    def update(self, request, *args, **kwargs):
        serializer = CommentSerializerForUpdate(instance=self.get_object(), data=request.data)
        if not serializer.is_valid():
            return Response({
                'message': 'error!',
                'errors': serializer.errors
            }, status=400)
        serializer.save()
        return Response({
            'message': 'successfully update'
        }, status=200)

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        comment.delete()
        return Response({'success': True}, status=200)


