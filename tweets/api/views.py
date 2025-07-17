from django.contrib.auth.models import User
from rest_framework import viewsets, permissions
from rest_framework.response import Response

from accounts.api.serializers import UserSerializerForTweetResponse
from newsfeeds.services import NewsFeedService
from tweets.api.serializers import TweetSerializerForCreate, TweetSerializer, TweetSerializerWithDetails, \
    TweetSerializerForUpdate
from tweets.models import Tweet
from utils.decorator import require_all_params
from utils.pagination import CustomEndlessPagination
from tweets.services import TweetService
from utils.rate_limiter import rate_limit
from utils.permissions import IsOwner


class TweetViewSet(viewsets.GenericViewSet):
    serializer_class = TweetSerializer
    queryset = Tweet.objects.all()
    pagination_class = CustomEndlessPagination

    def get_permissions(self):
        if self.action == 'list' or self.action == 'retrieve':
            return [permissions.AllowAny()]
        if self.action == 'update' or self.action == 'destroy':
            return [permissions.IsAuthenticated(), IsOwner()]
        return [permissions.IsAuthenticated()]

    @require_all_params(params=['user_id'])
    @rate_limit('3/s')
    def list(self, request):
        cached_tweets = TweetService.get_cached_tweets(user_id = request.query_params['user_id'])
        page = self.paginator.paginated_cached_list(cached_tweets, request)
        if page is None:
            query = Tweet.objects.filter(user_id = request.query_params['user_id']).order_by('-created_at')
            page = self.paginate_queryset(
                query)
        serializer = TweetSerializer(page, context = {'request': request}, many = True)
        return self.get_paginated_response(data=serializer.data)

    @rate_limit('3/s')
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
            'data': TweetSerializer(tweet, context={'request': request}).data,
            'id': tweet.id,
            'user': UserSerializerForTweetResponse(User.objects.get(id=tweet.user.id)).data,
        }, status=201)

    @rate_limit('3/s')
    def retrieve(self, request, pk=None):
        tweet = self.get_object()
        if not 'comment_limit' in request.query_params:
            return Response(TweetSerializerWithDetails(tweet, context={'request': request}).data)
        else:
            try:
                comment_limit = int(request.query_params['comment_limit'])
                if comment_limit < 0:
                    return Response({'success': False, 'error': 'comment_limit must be positive integer'}, status=400)
            except:
                return Response({'success': False, 'error': 'comment_limit must be integer'}, status=400)
            return Response(
                TweetSerializerWithDetails(tweet, context={'limit': comment_limit, 'request': request}).data)

    @rate_limit('3/s')
    def destroy(self, request, pk=None):
        tweet = self.get_object()
        tweet.delete()
        return Response({'success': True}, status=204)

    @require_all_params(params=['content'], request_attr='data')
    @rate_limit('3/s')
    def update(self, request, pk=None):
        tweet = self.get_object()
        serializer = TweetSerializerForUpdate(tweet, data=request.data, context={'request': request}, partial=True)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': serializer.errors,
            }, status=400)
        updated_tweet = serializer.save()
        return Response({
            'success': True,
            'data': TweetSerializer(updated_tweet, context={'request': request}).data,
        }, status=200)


