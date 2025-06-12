from django.contrib.auth.models import User
from rest_framework import viewsets, permissions, serializers
from rest_framework.response import Response

from accounts.api.serializers import UserSerializer, UserSerializerForTweetResponse
from tweets.api.serializers import TweetSerializerForCreate, TweetSerializer, TweetSerializerWithComments
from tweets.models import Tweet
from newsfeeds.services import NewsFeedService
from utils.decorator import require_all_params


class TweetViewSet(viewsets.GenericViewSet):
    serializer_class = TweetSerializerForCreate
    queryset = Tweet.objects.all()

    def get_permissions(self):
        if self.action == 'list' or self.action == 'retrieve':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @require_all_params(params=['user_id'])
    def list(self, request):
        tweets = Tweet.objects.filter(user_id = request.query_params['user_id']).order_by('-created_at')
        serializer = TweetSerializer(tweets, many=True)
        return Response({'tweets': serializer.data}, status = 200)

    def create(self, request):
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

    def retrieve(self, request, pk = None):
        tweet = self.get_object()
        if not 'comment_limit' in request.query_params:
            return Response(TweetSerializerWithComments(tweet).data)
        else:
            try:
                comment_limit = int(request.query_params['comment_limit'])
                if comment_limit < 0:
                    return Response({'success': False, 'error': 'comment_limit must be positive integer'}, status = 400)
            except:
                return Response({'success': False, 'error': 'comment_limit must be integer'}, status = 400)
            return Response(TweetSerializerWithComments(tweet, context={'limit':comment_limit}).data)








