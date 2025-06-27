from functools import wraps

from rest_framework import status
from rest_framework.response import Response


def require_all_params(request_attr='query_params', params=[]):
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            for param in params:
                if param not in getattr(request, request_attr):
                    return Response({'message': 'please check your data', 'errors': {param: ['is required']}},
                                    status=status.HTTP_400_BAD_REQUEST)
            return func(self, request, *args, **kwargs)

        return wrapper

    return decorator


def require_any_params(request_attr='query_params', params=[]):
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            for param in params:
                if param in getattr(request, request_attr):
                    print(getattr(request, request_attr))
                    return func(self, request, *args, **kwargs)
            return Response({'message': 'please check your data', 'errors': {str(params): ['require at least one param']}},
                            status=status.HTTP_400_BAD_REQUEST)
        return wrapper
    return decorator
