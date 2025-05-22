from rest_framework import viewsets, permissions, serializers
from rest_framework.response import Response

from tweets.api.serializers import TweetCreateSerializer, TweetSerializer
from tweets.models import Tweet



class TweetViewSet(viewsets.GenericViewSet):
    serializer_class = TweetCreateSerializer

    def get_permissions(self):
        if self.action == 'list':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def list(self, request):
        if 'user_id' not in request.query_params:
            return Response('user_id is required', status = 400)
        tweets = Tweet.objects.filter(user_id = request.query_params['user_id']).order_by('-created_at')
        serializer = TweetSerializer(tweets, many=True)
        return Response({'tweets': serializer.data}, status = 200)






