from rest_framework import viewsets, permissions
from rest_framework.response import Response

from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.models import NewsFeed
from utils.pagination import CustomEndlessPagination
from newsfeeds.services import NewsFeedService


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = CustomEndlessPagination
    queryset = NewsFeed.objects.all()

    def list(self, request):
        cached_newsfeeds = NewsFeedService.get_cached_newsfeed(user_id = request.user.id)
        page = self.paginator.paginated_cached_list(cached_newsfeeds, request)
        if not page:
            queryset = NewsFeed.objects.filter(user_id = request.user.id).order_by('-created_at')
            page = self.paginator.paginate_queryset(queryset, request)
        serializer = NewsFeedSerializer(page, many = True, context = {'request': request})
        return self.get_paginated_response(data=serializer.data)

