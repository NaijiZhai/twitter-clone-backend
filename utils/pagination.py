from rest_framework.pagination import PageNumberPagination, BasePagination
from rest_framework.response import Response


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

    def get_paginated_response(self, data):
        return Response({
            'results': data,
            'has_next_page': self.has_next_page
        })


