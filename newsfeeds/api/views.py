from rest_framework import viewsets, permissions
from rest_framework.response import Response
from dateutil import parser

from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.models import NewsFeed
from utils.pagination import CustomEndlessPagination
from newsfeeds.services import NewsFeedService
from utils.rate_limiter import rate_limit


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = CustomEndlessPagination
    queryset = NewsFeed.objects.all()

    @rate_limit('10/s')
    def list(self, request):
        max_tweet_id = request.GET.get('max_tweet_id')
        if max_tweet_id:
            max_tweet_id = int(max_tweet_id)


        # for pagination
        created_at_lt = request.GET.get('created_at__lt')
        created_at_gt = request.GET.get('created_at__gt')

        created_at_lt_datetime = None
        created_at_gt_datetime = None

        if created_at_lt:
            try:
                created_at_lt_datetime = parser.isoparse(created_at_lt)
            except (ValueError, TypeError):
                pass

        if created_at_gt:
            try:
                created_at_gt_datetime = parser.isoparse(created_at_gt)
            except (ValueError, TypeError):
                pass

        # fetch one more to check if there is another page
        fetch_count = self.paginator.page_size + 1
        newsfeeds = NewsFeedService.get_newsfeed_hybrid(
            user_id=request.user.id,
            max_tweet_id=max_tweet_id,
            count=fetch_count,
            created_at_lt=created_at_lt_datetime,
            created_at_gt=created_at_gt_datetime
        )

        has_next_page = len(newsfeeds) > self.paginator.page_size
        results = newsfeeds[:self.paginator.page_size]

        serializer = NewsFeedSerializer(results, many=True, context={'request': request})

        return Response({
            'results': serializer.data,
            'has_next_page': has_next_page
        })