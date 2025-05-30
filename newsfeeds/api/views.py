from rest_framework import viewsets, permissions
from rest_framework.response import Response

from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.models import NewsFeed


class NewsFeedViewSet(viewsets.ViewSet):
    permission_classes = (permissions.IsAuthenticated,)


    def get_queryset(self):
        return NewsFeed.objects.filter(user = self.request.user).order_by('-created_at')

    def list(self, request):
        queryset = self.get_queryset()
        return Response({'newsfeeds': NewsFeedSerializer(queryset, many=True).data})

