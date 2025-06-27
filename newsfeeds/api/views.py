from rest_framework import viewsets, permissions
from rest_framework.response import Response

from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.models import NewsFeed
from utils.pagination import CustomEndlessPagination


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = CustomEndlessPagination


    def get_queryset(self):
        return NewsFeed.objects.filter(user = self.request.user).order_by('-created_at')

    def list(self, request):
        queryset = self.get_queryset()
        queryset = self.paginate_queryset(queryset)
        return self.get_paginated_response(NewsFeedSerializer(queryset, many=True).data)

