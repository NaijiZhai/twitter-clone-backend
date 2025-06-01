from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response

from comments.models import Comment


# Create your views here.
class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()

    def list(self, request, *args, **kwargs):
        params = request.query_params
        if 'tweet' not in params:
            return Response({
                'message': 'Tweet required',
            }, status=status.HTTP_400_BAD_REQUEST)


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response({'message' : serializer.errors}, status=400)
        serializer.save()
        return Response(
            {
                'success': True,
                'data': serializer.data,
            },
            status=201
        )
