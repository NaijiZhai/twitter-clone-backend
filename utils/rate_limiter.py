# ratelimit.py
import time
import functools
import redis
from django.http import JsonResponse
from django.conf import settings
from typing import Optional, Callable


class RateLimiter:
    """Redis-based rate limiter"""

    def __init__(self, redis_client=None, host='localhost', port=6379, db=11):
        if redis_client:
            # Use provided Redis client
            self.redis_client = redis_client
        else:
            # Try to get config from settings, otherwise use defaults
            self.redis_client = redis.Redis(
                host=getattr(settings, 'RATELIMIT_REDIS_HOST', host),
                port=getattr(settings, 'RATELIMIT_REDIS_PORT', port),
                db=getattr(settings, 'RATELIMIT_REDIS_DB', db),
                password=getattr(settings, 'RATELIMIT_REDIS_PASSWORD', None),
                decode_responses=True
            )

    def _parse_rate(self, rate: str) -> tuple:
        """
        Parse rate string like '10/s', '100/m', '1000/h'
        Returns (count, seconds)
        """
        parts = rate.split('/')
        if len(parts) != 2:
            raise ValueError(f"Invalid rate format: {rate}")

        count = int(parts[0])
        period = parts[1].lower()

        period_seconds = {
            's': 1,  # seconds
            'm': 60,  # minutes
            'h': 3600,  # hours
        }

        if period not in period_seconds:
            raise ValueError(f"Invalid period: {period}. Use 's', 'm', or 'h'")

        return count, period_seconds[period]

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: int) -> tuple:
        """
        Check rate limit
        Returns (allowed, remaining_requests, reset_time)
        """
        now = time.time()
        window_start = now - window_seconds

        # Use Redis sliding window algorithm (sorted set)
        pipe = self.redis_client.pipeline()

        # Remove expired request records
        pipe.zremrangebyscore(key, 0, window_start)

        # Get request count in current window
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(now): now})

        # Set expiration time
        pipe.expire(key, window_seconds + 1)

        results = pipe.execute()
        request_count = results[1]

        # Check if limit exceeded
        if request_count >= max_requests:
            remaining = 0
            # Get earliest request time to calculate reset time
            earliest = self.redis_client.zrange(key, 0, 0, withscores=True)
            if earliest:
                reset_time = earliest[0][1] + window_seconds
            else:
                reset_time = now + window_seconds

            # Remove the request we just added if over limit
            self.redis_client.zrem(key, str(now))

            return False, remaining, int(reset_time)
        else:
            remaining = max_requests - request_count - 1
            reset_time = now + window_seconds
            return True, remaining, int(reset_time)


def get_client_ip(request):
    """Get client's real IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # If behind proxy, get first IP
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        # Direct connection
        ip = request.META.get('REMOTE_ADDR', 'unknown')
    return ip


def rate_limit(rate: str,
               key_func: Optional[Callable] = None,
               error_message: str = "Rate limit exceeded. Please try again later.",
               key_prefix: str = "rl",
               redis_client=None,
               redis_host='localhost',
               redis_port=6379,
               redis_db=11) -> Callable:
    """
    Decorator to add rate limiting to view functions

    Args:
        rate: Rate limit like '10/s', '100/m', '1000/h'
        key_func: Function to generate identifier, defaults to IP address
        error_message: Error message when limit exceeded
        key_prefix: Redis key prefix
        redis_client: Custom Redis client instance
        redis_host: Redis host (used when redis_client is None)
        redis_port: Redis port (used when redis_client is None)
        redis_db: Redis database number (used when redis_client is None)

    Examples:
        # 1. Use default config or settings config
        @rate_limit('10/s')
        def my_view(request):
            return JsonResponse({'status': 'ok'})

        # 2. Use custom Redis connection
        custom_redis = redis.Redis(host='10.0.0.1', port=6380, db=2)
        @rate_limit('60/m', redis_client=custom_redis)
        def api_view(request):
            return JsonResponse({'data': 'some data'})

        # 3. Specify connection parameters directly
        @rate_limit('100/h', redis_host='10.0.0.1', redis_port=6380, redis_db=2)
        def another_view(request):
            return JsonResponse({'status': 'ok'})

        # 4. Use Django-Redis connection
        from django_redis import get_redis_connection
        @rate_limit('30/m', redis_client=get_redis_connection("ratelimit"))
        def cached_view(request):
            return JsonResponse({'cached': True})
    """
    limiter = RateLimiter(redis_client=redis_client, host=redis_host, port=redis_port, db=redis_db)
    max_requests, window_seconds = limiter._parse_rate(rate)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            # Get identifier
            if key_func:
                identifier = str(key_func(request))
            else:
                # Default to IP address
                identifier = get_client_ip(request)

            # Generate Redis key
            key = f"{key_prefix}:{func.__name__}:{identifier}"

            # Check rate limit
            allowed, remaining, reset_time = limiter.check_rate_limit(key, max_requests, window_seconds)

            if allowed:
                # Execute original function
                response = func(request, *args, **kwargs)
            else:
                # Return 429 error
                retry_after = reset_time - int(time.time())
                response = JsonResponse({
                    'error': error_message,
                    'retry_after': retry_after
                }, status=429)

            # Add rate limit headers
            response['X-RateLimit-Limit'] = rate
            response['X-RateLimit-Remaining'] = str(remaining)
            response['X-RateLimit-Reset'] = str(reset_time)

            return response

        return wrapper

    return decorator


# Usage examples and configuration
"""
# settings.py configuration (optional)
# Use dedicated config names to avoid conflicts with other Redis configs
RATELIMIT_REDIS_HOST = 'localhost'  # Redis server address
RATELIMIT_REDIS_PORT = 6379         # Redis port
RATELIMIT_REDIS_DB = 1              # Redis database number (recommend using different DB)
RATELIMIT_REDIS_PASSWORD = None     # Redis password (if needed)

# Or use existing Redis connection pool
from django_redis import get_redis_connection
redis_conn = get_redis_connection("default")  # Use Django-Redis connection

# views.py usage examples
from django.http import JsonResponse
from .ratelimit import rate_limit, get_client_ip
import redis

# 1. Simple IP-based limiting (uses RATELIMIT_REDIS_* settings)
@rate_limit('10/s')  # Max 10 requests per second per IP
def api_endpoint(request):
    return JsonResponse({'message': 'Success', 'your_ip': get_client_ip(request)})

# 2. Use custom Redis client
custom_redis = redis.Redis(host='10.0.0.1', port=6380, db=2, password='mypassword')
@rate_limit('100/m', redis_client=custom_redis)
def custom_redis_api(request):
    return JsonResponse({'custom': True})

# 3. Use Django-Redis connection pool (if you're already using Django-Redis)
try:
    from django_redis import get_redis_connection
    @rate_limit('50/m', redis_client=get_redis_connection("ratelimit"))
    def pooled_api(request):
        return JsonResponse({'pooled': True})
except ImportError:
    pass

# 4. Different time windows
@rate_limit('100/m')  # Max 100 requests per minute per IP
def search_api(request):
    query = request.GET.get('q', '')
    return JsonResponse({'query': query, 'results': []})

@rate_limit('1000/h')  # Max 1000 requests per hour per IP
def data_api(request):
    return JsonResponse({'data': 'some data'})

# 5. Custom error message
@rate_limit('5/m', error_message='Too many requests, please slow down')
def sensitive_api(request):
    return JsonResponse({'sensitive': 'data'})

# 6. User-based limiting (requires authentication)
@rate_limit('50/h', key_func=lambda r: r.user.id if r.user.is_authenticated else f'anon:{get_client_ip(r)}')
def user_specific_api(request):
    return JsonResponse({
        'user': request.user.username if request.user.is_authenticated else 'anonymous',
        'data': 'user specific data'
    })

# 7. Multiple limits (using multiple decorators)
@rate_limit('10/s')   # Per second limit
@rate_limit('50/m')   # Per minute limit
@rate_limit('500/h')  # Per hour limit
def multi_limit_api(request):
    return JsonResponse({'status': 'ok'})

# 8. IP + endpoint based limiting
@rate_limit('20/m', key_func=lambda r: f"{get_client_ip(r)}:{r.method}")
def method_specific_api(request):
    return JsonResponse({'method': request.method})

# 9. API Key + IP combination limiting
@rate_limit('100/h', key_func=lambda r: f"{r.headers.get('X-API-Key', 'no-key')}:{get_client_ip(r)}")
def api_key_endpoint(request):
    api_key = request.headers.get('X-API-Key', 'no-key')
    return JsonResponse({'api_key': api_key, 'status': 'ok'})
"""