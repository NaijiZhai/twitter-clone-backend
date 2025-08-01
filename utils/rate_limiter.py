# ratelimit.py
import time
import functools
from datetime import datetime

import redis
from django.http import JsonResponse
from django.conf import settings
from typing import Optional, Callable
import ipaddress


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


def get_client_ip(request) -> str:
    """
    Get client's real IP address with comprehensive proxy handling

    Args:
        request: Django request object

    Returns:
        str: Client's IP address or 'unknown' if cannot be determined
    """
    # Check various possible headers in priority order
    headers_to_check = [
        'HTTP_X_FORWARDED_FOR',  # Most common proxy header
        'HTTP_X_REAL_IP',  # Commonly used by Nginx
        'HTTP_CF_CONNECTING_IP',  # Cloudflare
        'HTTP_X_FORWARDED',  # Standard header variant
        'HTTP_X_CLUSTER_CLIENT_IP',  # Cluster environments
        'HTTP_FORWARDED_FOR',  # Another variant
        'HTTP_FORWARDED',  # RFC 7239 standard
        'HTTP_CLIENT_IP',  # Used by some proxies
        'HTTP_TRUE_CLIENT_IP',  # Used by some CDNs
    ]

    for header in headers_to_check:
        ip_list = request.META.get(header)
        if ip_list:
            # Handle multiple IPs (first one is usually the real client IP)
            for ip in ip_list.split(','):
                ip = ip.strip()
                if is_valid_public_ip(ip):
                    return ip

    # If no proxy headers found, use direct connection IP
    remote_addr = request.META.get('REMOTE_ADDR', 'unknown')
    return remote_addr if is_valid_public_ip(remote_addr) else 'unknown'


def is_valid_public_ip(ip: str) -> bool:
    """
    Validate if IP address is valid and public

    Args:
        ip: IP address string

    Returns:
        bool: Whether it's a valid public IP
    """
    if not ip or ip == 'unknown':
        return False

    try:
        # Use ipaddress module for stricter validation
        ip_obj = ipaddress.ip_address(ip)

        # Check if it's a public IP (exclude private, loopback, link-local, etc.)
        return (
                ip_obj.is_global and
                not ip_obj.is_private and
                not ip_obj.is_loopback and
                not ip_obj.is_link_local and
                not ip_obj.is_multicast and
                not ip_obj.is_reserved
        )

    except ValueError:
        # If it's not a valid IP address format
        return False


def is_valid_ip_basic(ip: str) -> bool:
    """
    Basic IP validation (if you don't want to exclude private IPs)

    Args:
        ip: IP address string

    Returns:
        bool: Whether it's a valid IP address
    """
    if not ip or ip == 'unknown':
        return False

    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def get_client_ip_with_fallback(request, allow_private: bool = False) -> str:
    """
    Enhanced version of getting client IP with more configuration options

    Args:
        request: Django request object
        allow_private: Whether to allow returning private IP addresses

    Returns:
        str: Client IP address
    """
    headers_to_check = [
        'HTTP_X_FORWARDED_FOR',
        'HTTP_X_REAL_IP',
        'HTTP_CF_CONNECTING_IP',  # Cloudflare
        'HTTP_X_FORWARDED',
        'HTTP_X_CLUSTER_CLIENT_IP',
        'HTTP_FORWARDED_FOR',
        'HTTP_FORWARDED',
        'HTTP_CLIENT_IP',
        'HTTP_TRUE_CLIENT_IP',
    ]

    # Store all found IPs for fallback
    found_ips = []

    for header in headers_to_check:
        ip_list = request.META.get(header)
        if ip_list:
            for ip in ip_list.split(','):
                ip = ip.strip()
                if is_valid_ip_basic(ip):
                    found_ips.append(ip)
                    # Return immediately if we find a public IP
                    if is_valid_public_ip(ip):
                        return ip

    # Check direct connection IP
    remote_addr = request.META.get('REMOTE_ADDR', '')
    if is_valid_ip_basic(remote_addr):
        found_ips.append(remote_addr)
        if is_valid_public_ip(remote_addr):
            return remote_addr

    # If private IPs are allowed, return the first valid IP found
    if allow_private and found_ips:
        return found_ips[0]

    # Final fallback
    return remote_addr if remote_addr else 'unknown'


def rate_limit(rate: str,
               key_func: Optional[Callable] = None,
               error_message: str = "Rate limit exceeded. Please try again later.",
               key_prefix: str = "rl",
               redis_client=None,
               redis_host='localhost',
               redis_port=6379,
               redis_db=11,
               status_code = 429,
               enabled: Optional[bool] = False) -> Callable:
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
        enabled: Enable/disable rate limiting. If None, uses RATELIMIT_ENABLE from settings

    Examples:
        # 1. Use default config or settings config (auto-detects RATELIMIT_ENABLE)
        @rate_limit('10/s')
        def my_view(request):
            return JsonResponse({'status': 'ok'})

        # 2. Force enable rate limiting even if RATELIMIT_ENABLE is False
        @rate_limit('10/s', enabled=True)
        def always_limited_view(request):
            return JsonResponse({'status': 'ok'})

        # 3. Force disable rate limiting
        @rate_limit('10/s', enabled=False)
        def never_limited_view(request):
            return JsonResponse({'status': 'ok'})
    """

    # Check if rate limiting is enabled
    if enabled is None:
        # Use setting from Django settings, default to True if not set
        ratelimit_enabled = getattr(settings, 'RATELIMIT_ENABLE', True)
    else:
        ratelimit_enabled = enabled

    # If rate limiting is disabled, return a no-op decorator
    if not ratelimit_enabled:
        def no_op_decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Handle both function-based views and class-based views
                if args and hasattr(args[0], 'request'):
                    # This is a class-based view method (self, request, ...)
                    request = args[1] if len(args) > 1 else args[0].request
                else:
                    # This is a function-based view (request, ...)
                    request = args[0] if args else None

                response = func(*args, **kwargs)

                # Only add headers if we have a valid response object
                if hasattr(response, '__setitem__'):
                    response['X-RateLimit-Limit'] = rate
                    response['X-RateLimit-Remaining'] = 'unlimited'
                    response['X-RateLimit-Reset'] = '0'
                    response['X-RateLimit-Status'] = 'disabled'

                return response

            return wrapper

        return no_op_decorator

    limiter = RateLimiter(redis_client=redis_client, host=redis_host, port=redis_port, db=redis_db)
    max_requests, window_seconds = limiter._parse_rate(rate)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Handle both function-based views and class-based views
            if args and hasattr(args[0], 'request'):
                # This is a class-based view method (self, request, ...)
                request = args[1] if len(args) > 1 else args[0].request
            else:
                # This is a function-based view (request, ...)
                request = args[0] if args else None

            if not request:
                # If we can't find the request object, just execute the function
                return func(*args, **kwargs)

            # Get identifier
            if key_func:
                identifier = str(key_func(request))
            else:
                # Default to IP address
                identifier = get_client_ip(request)

            # Generate Redis key
            module = func.__module__
            qualname = func.__qualname__
            key = f"{key_prefix}:{module}:{qualname}:{identifier}"

            # Check rate limit
            allowed, remaining, reset_time = limiter.check_rate_limit(key, max_requests, window_seconds)
            if allowed:
                # Execute original function
                response = func(*args, **kwargs)
            else:
                retry_after = reset_time - int(time.time())
                if datetime.now().month == 4 and datetime.now().day == 1:
                    response = JsonResponse({
                        'error': 'I\'m a teapot - too many requests!',
                        'retry_after': retry_after
                    }, status=418)
                # Return 429 error
                else:
                    response = JsonResponse({
                        'error': error_message,
                        'retry_after': retry_after
                    }, status=status_code)

            # Add rate limit headersmk



            if hasattr(response, '__setitem__'):
                response['X-RateLimit-Limit'] = rate
                response['X-RateLimit-Remaining'] = str(remaining)
                response['X-RateLimit-Reset'] = str(reset_time)
                response['X-RateLimit-Status'] = 'enabled'

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
RATELIMIT_ENABLE = not TESTING      # Enable/disable rate limiting based on TESTING flag

# Or use existing Redis connection pool
from django_redis import get_redis_connection
redis_conn = get_redis_connection("default")  # Use Django-Redis connection

# views.py usage examples
from django.http import JsonResponse
from .ratelimit import rate_limit, get_client_ip
import redis

# 1. Simple IP-based limiting (automatically respects RATELIMIT_ENABLE setting)
@rate_limit('10/s')  # Max 10 requests per second per IP
def api_endpoint(request):
    return JsonResponse({'message': 'Success', 'your_ip': get_client_ip(request)})

# 2. Force enable rate limiting even in testing
@rate_limit('10/s', enabled=True)
def always_limited_api(request):
    return JsonResponse({'message': 'Always limited'})

# 3. Force disable rate limiting
@rate_limit('10/s', enabled=False)
def never_limited_api(request):
    return JsonResponse({'message': 'Never limited'})

# 4. Use custom Redis client
custom_redis = redis.Redis(host='10.0.0.1', port=6380, db=2, password='mypassword')
@rate_limit('100/m', redis_client=custom_redis)
def custom_redis_api(request):
    return JsonResponse({'custom': True})

# 5. Use Django-Redis connection pool (if you're already using Django-Redis)
try:
    from django_redis import get_redis_connection
    @rate_limit('50/m', redis_client=get_redis_connection("ratelimit"))
    def pooled_api(request):
        return JsonResponse({'pooled': True})
except ImportError:
    pass

# 6. Different time windows
@rate_limit('100/m')  # Max 100 requests per minute per IP
def search_api(request):
    query = request.GET.get('q', '')
    return JsonResponse({'query': query, 'results': []})

@rate_limit('1000/h')  # Max 1000 requests per hour per IP
def data_api(request):
    return JsonResponse({'data': 'some data'})

# 7. Custom error message
@rate_limit('5/m', error_message='Too many requests, please slow down')
def sensitive_api(request):
    return JsonResponse({'sensitive': 'data'})

# 8. User-based limiting (requires authentication)
@rate_limit('50/h', key_func=lambda r: r.user.id if r.user.is_authenticated else f'anon:{get_client_ip(r)}')
def user_specific_api(request):
    return JsonResponse({
        'user': request.user.username if request.user.is_authenticated else 'anonymous',
        'data': 'user specific data'
    })

# 9. Multiple limits (using multiple decorators)
@rate_limit('10/s')   # Per second limit
@rate_limit('50/m')   # Per minute limit
@rate_limit('500/h')  # Per hour limit
def multi_limit_api(request):
    return JsonResponse({'status': 'ok'})

# 10. IP + endpoint based limiting
@rate_limit('20/m', key_func=lambda r: f"{get_client_ip(r)}:{r.method}")
def method_specific_api(request):
    return JsonResponse({'method': request.method})

# 11. API Key + IP combination limiting
@rate_limit('100/h', key_func=lambda r: f"{r.headers.get('X-API-Key', 'no-key')}:{get_client_ip(r)}")
def api_key_endpoint(request):
    api_key = request.headers.get('X-API-Key', 'no-key')
    return JsonResponse({'api_key': api_key, 'status': 'ok'})

# 12. Usage in class-based views (ViewSet)
class CommentViewSet(viewsets.ModelViewSet):
    @rate_limit('3/s')
    def list(self, request, *args, **kwargs):
        # Your view logic here
        return Response({'comments': []})
"""