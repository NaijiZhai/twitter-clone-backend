from dateutil import parser
from rest_framework.pagination import PageNumberPagination, BasePagination
from rest_framework.response import Response

from cache_utils.cache_constants import REDIS_LIST_LIMIT_LENGTH


class CustomPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'size'
    max_page_size = 20
    page_query_param = 'page'

    def get_paginated_response(self, data):
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': self.page.paginator.count,
            'results': data,
            'page_number': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            'total_results': self.page.paginator.count,
            'has_next_page': self.page.has_next(),
        })

class CustomEndlessPagination(BasePagination):
    page_size = 20

    def __init__(self):
        super(CustomEndlessPagination, self).__init__()
        self.has_next_page = False

    def to_html(self):
        pass

    def paginate_queryset(self, queryset, request, view=None):
        if 'created_at__lt' in request.query_params:
            queryset = queryset.filter(created_at__lt=request.query_params['created_at__lt'])
            self.has_next_page = False
            return queryset.order_by('-created_at')

        if 'created_at__gt' in request.query_params:
            queryset = queryset.filter(created_at__gt=request.query_params['created_at__gt'])

        results = list(queryset[: self.page_size + 1])
        self.has_next_page = len(results) > self.page_size
        return results[: self.page_size]

    def paginated_ordered_list(self, queryset, request):
        if 'created_at__gt' in request.query_params:
            created_at__gt = parser.isoparse(request.query_params['created_at__gt'])
            objects = []
            for obj in queryset:
                if obj.created_at > created_at__gt:
                    objects.append(obj)
                else:
                    break
            self.has_next_page = False
            return objects

        index = 0
        if 'created_at__lt' in request.query_params:
            created_at__lt = parser.isoparse(request.query_params['created_at__lt'])
            for index, obj in enumerate(queryset):
                if obj.created_at < created_at__lt:
                    break
            else:
                # If no matching object is found, index should be the length of the list
                index = len(queryset)

        # Extract one page of data
        page_data = queryset[index: index + self.page_size]

        # Check if there is more data beyond the current page
        remaining_data = queryset[index + self.page_size:]
        self.has_next_page = len(remaining_data) > 0

        return page_data

    def paginated_cached_list(self, cached_list, request):
        paginated_list = self.paginated_ordered_list(cached_list, request)

        # For the latest data
        if 'created_at__gt' in request.query_params:
            return paginated_list

        # If pagination already has more data, return directly
        if self.has_next_page:
            return paginated_list

        # If the cache contains all available data, return directly
        if len(cached_list) < REDIS_LIST_LIMIT_LENGTH:
            return paginated_list

        return None

    def get_paginated_response(self, data):
        return Response({
            'results': data,
            'has_next_page': self.has_next_page
        })


