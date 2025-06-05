from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from comments.api.serializers import CommentSerializerForCreate, CommentSerializer
from comments.models import Comment


# Create your views here.
class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializerForCreate

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        return [AllowAny()]

    def list(self, request, *args, **kwargs):
        params = request.query_params
        if 'tweet' not in params:
            return Response({
                'message': 'Tweet required',
            }, status=status.HTTP_400_BAD_REQUEST)


    def create(self, request, *args, **kwargs):

        data = {
            'user_id': request.user.id,
            'tweet_id': request.data.get('tweet_id'),
            'content': request.data.get('content'),
        }
        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            return Response({'message' : 'error', 'errors':serializer.errors}, status=400)
        comment = serializer.save()
        return Response(
                CommentSerializer(comment).data,
            status=201
        )

