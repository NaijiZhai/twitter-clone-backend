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
        user_id = request.query_params['user_id']

        # 🔍 使用与NewsFeed类似的简化分页逻辑
        # 如果有分页参数，直接查询数据库，不使用缓存
        if 'created_at__lt' in request.query_params or 'created_at__gt' in request.query_params:
            query = Tweet.objects.filter(user_id=user_id).order_by('-created_at')

            # 应用时间过滤
            if 'created_at__lt' in request.query_params:
                query = query.filter(created_at__lt=request.query_params['created_at__lt'])
            if 'created_at__gt' in request.query_params:
                query = query.filter(created_at__gt=request.query_params['created_at__gt'])

            # 获取分页大小+1的数据来判断是否有下一页
            fetch_count = self.paginator.page_size + 1
            results = list(query[:fetch_count])
            has_next_page = len(results) > self.paginator.page_size
            page = results[:self.paginator.page_size]

            # 设置分页器的状态
            self.paginator.has_next_page = has_next_page

            serializer = TweetSerializer(page, context={'request': request}, many=True)
            return Response({
                'results': serializer.data,
                'has_next_page': has_next_page
            })

        # 没有分页参数，尝试使用缓存
        cached_tweets = TweetService.get_cached_tweets(user_id=user_id)

        # 简化缓存逻辑：直接判断缓存是否足够
        fetch_count = self.paginator.page_size + 1

        if len(cached_tweets) >= fetch_count:
            # 缓存足够，直接使用缓存
            has_next_page = len(cached_tweets) > self.paginator.page_size
            page = cached_tweets[:self.paginator.page_size]
            self.paginator.has_next_page = has_next_page
        else:
            # 缓存不够或为空，查询数据库
            query = Tweet.objects.filter(user_id=user_id).order_by('-created_at')
            results = list(query[:fetch_count])
            has_next_page = len(results) > self.paginator.page_size
            page = results[:self.paginator.page_size]
            self.paginator.has_next_page = has_next_page

        serializer = TweetSerializer(page, context={'request': request}, many=True)
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