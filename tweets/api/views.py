from django.contrib.auth.models import User
from rest_framework import viewsets, permissions, serializers
from rest_framework.response import Response

from accounts.api.serializers import UserSerializer, UserSerializerForTweetResponse
from tweets.api.serializers import TweetSerializerForCreate, TweetSerializer
from tweets.models import Tweet
from newsfeeds.services import NewsFeedService



class TweetViewSet(viewsets.GenericViewSet):
    serializer_class = TweetSerializerForCreate

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

    def create(self, request):
        print(request)
        serializer = TweetSerializerForCreate(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': serializer.errors,
            }, status=400)
        tweet = serializer.save()
        NewsFeedService.fanout_to_followers(tweet)
        return Response({
            'success': True,
            'data': TweetSerializer(tweet).data,
            'id': tweet.id,
            'user' : UserSerializerForTweetResponse(User.objects.get(id = tweet.user.id)).data,
        }, status = 201)







