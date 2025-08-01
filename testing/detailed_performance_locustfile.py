#!/usr/bin/env python
"""
Performance Testing Script for Twitter Clone

Tests various performance metrics including:
- API response times (cached vs uncached)
- Cache hit rates
- Tweet creation and fanout performance
- Database query efficiency
"""

import os
import sys
import time
import json
import random
import requests
import statistics
from datetime import timedelta
from django.utils import timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'twitter.settings')

import django

django.setup()

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.test import Client
from friendships.models import Friendship
from tweets.models import Tweet
from newsfeeds.models import NewsFeed


class PerformanceTestRunner:
    """Run comprehensive performance tests"""

    def __init__(self, base_url='http://localhost:8000'):
        self.base_url = base_url
        self.client = Client()
        self.results = {
            'cache_performance': {},
            'api_response_times': {},
            'fanout_performance': {},
            'database_metrics': {},
            'load_test_results': {}
        }

    def setup_test_users(self):
        """Get test users for performance testing"""
        print("🔧 Setting up test users...")

        self.test_users = {
            'celebrity': User.objects.filter(username__startswith='celebrity_').first(),
            'influencer': User.objects.filter(username__startswith='influencer_').first(),
            'active': User.objects.filter(username__startswith='active_').first(),
            'normal': User.objects.filter(username__startswith='normal_').first(),
            'lurker': User.objects.filter(username__startswith='lurker_').first()
        }

        # Get follower counts
        for user_type, user in self.test_users.items():
            if user:
                follower_count = Friendship.objects.filter(to_user=user).count()
                print(f"   • {user_type}: {user.username} ({follower_count} followers)")

    def test_cache_performance(self):
        """Test cache hit rates and performance"""
        print("\n📊 Testing Cache Performance...")

        # Clear cache first
        cache.clear()

        # Get active users (logged in within 24 hours)
        active_users = User.objects.filter(
            last_login__gte=timezone.now() - timedelta(hours=24)
        )
        total_users = User.objects.count()

        print(f"   Active users: {active_users.count()} / {total_users}")

        # Skip warmup if cache is already warm
        print("   Checking if cache is already warm...")
        sample_users = active_users[:10]
        already_cached = sum(1 for u in sample_users if cache.get(f'newsfeed:{u.id}'))

        if already_cached < 8:  # Less than 80% cached
            print("   Cache is cold, warming up...")
            warmup_start = time.time()

            cached_count = 0
            for user in active_users[:100]:  # Test with first 100 active users
                # Simulate caching newsfeed
                cache_key = f'newsfeed:{user.id}'
                # Get user's newsfeed data
                following = Friendship.objects.filter(from_user=user).values_list('to_user', flat=True)
                recent_tweets = Tweet.objects.filter(
                    user__in=following
                ).order_by('-created_at')[:20]

                # Cache the data (simulating your ~500 bytes per entry)
                cache_data = [
                    {
                        'id': tweet.id,
                        'user': tweet.user.username,
                        'content': tweet.content[:100],  # Truncate for size
                        'created_at': tweet.created_at.isoformat()
                    }
                    for tweet in recent_tweets
                ]

                cache.set(cache_key, cache_data, timeout=86400)  # 24 hour TTL
                cached_count += 1

            warmup_time = time.time() - warmup_start
        else:
            print("   Cache is already warm, skipping warmup")
            cached_count = active_users.count()
            warmup_time = 0

        # Test cache hits
        print("   Testing cache hit rates...")
        cache_hits = 0
        cache_misses = 0
        response_times = []

        # Test with mix of active and inactive users to simulate real usage
        # 70% from active users, 30% from all users
        active_sample_size = 140
        inactive_sample_size = 60

        # Get active users sample
        active_sample = active_users.order_by('?')[:active_sample_size]

        # Get some potentially inactive users
        all_users_sample = User.objects.exclude(
            id__in=active_users.values_list('id', flat=True)
        ).order_by('?')[:inactive_sample_size]

        # Combine samples
        test_sample = list(active_sample) + list(all_users_sample)
        random.shuffle(test_sample)

        for user in test_sample:
            start = time.time()
            cache_key = f'newsfeed:{user.id}'

            cached_data = cache.get(cache_key)
            if cached_data:
                cache_hits += 1
                # Actually use the cached data to simulate real usage
                # This ensures we're measuring realistic cache performance
                tweet_count = len(cached_data) if isinstance(cached_data, list) else 0
            else:
                cache_misses += 1
                # Simulate DB query for cache miss
                following = Friendship.objects.filter(from_user=user).values_list('to_user', flat=True)
                tweets = list(Tweet.objects.filter(user__in=following).order_by('-created_at')[:20])
                tweet_count = len(tweets)

            response_times.append((time.time() - start) * 1000)  # Convert to ms

        # Calculate metrics
        hit_rate = (cache_hits / (cache_hits + cache_misses)) * 100 if (cache_hits + cache_misses) > 0 else 0
        avg_response_time = statistics.mean(response_times) if response_times else 0

        self.results['cache_performance'] = {
            'active_users': active_users.count(),
            'total_users': total_users,
            'active_user_percentage': (active_users.count() / total_users) * 100,
            'test_sample_size': len(test_sample),
            'active_in_sample': active_sample_size,
            'cache_warmup_time': f"{warmup_time:.2f}s" if warmup_time > 0 else "Skipped (already warm)",
            'cache_hit_rate': f"{hit_rate:.1f}%",
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'avg_response_time': f"{avg_response_time:.2f}ms",
            'p95_response_time': f"{statistics.quantiles(response_times, n=20)[18]:.2f}ms" if len(
                response_times) > 20 else "N/A"
        }

        print(f"   ✅ Cache hit rate: {hit_rate:.1f}%")
        print(f"   ✅ Average response time: {avg_response_time:.2f}ms")

    def test_api_response_times(self):
        """Test actual API endpoint response times"""
        print("\n⚡ Testing API Response Times...")

        endpoints = [
            ('GET', '/api/newsfeeds/', 'Timeline (cached user)', {}),
            ('GET', '/api/newsfeeds/', 'Timeline (uncached user)', {}),
            ('POST', '/api/tweets/', 'Create tweet', {'content': 'Performance test tweet'}),
            ('GET', '/api/friendships/', 'Get followers', {}),  # Will add to_user_id param
            ('GET', '/api/friendships/', 'Get following', {}),  # Will add from_user_id param
        ]

        results = {}

        for method, endpoint, description, params in endpoints:
            print(f"   Testing {description}...")

            # Choose appropriate test user
            if 'cached' in description:
                # Use an active user likely to be cached
                test_user = User.objects.filter(
                    username__startswith='active_',
                    last_login__gte=timezone.now() - timedelta(hours=24)
                ).first()
            elif 'uncached' in description:
                # Use a lurker unlikely to be cached
                test_user = User.objects.filter(
                    username__startswith='lurker_'
                ).first()
            else:
                test_user = self.test_users['normal']

            if not test_user:
                continue

            # Login as test user
            self.client.force_login(test_user)

            # Special handling for friendships endpoint
            if 'friendships' in endpoint:
                if 'followers' in description:
                    # Test getting followers (who follows this user)
                    endpoint = f'/api/friendships/?to_user_id={test_user.id}'
                else:
                    # Test getting following (who this user follows)
                    endpoint = f'/api/friendships/?from_user_id={test_user.id}'

            response_times = []

            # Run multiple tests
            for i in range(10):
                start = time.time()

                if method == 'GET':
                    response = self.client.get(endpoint)
                elif method == 'POST':
                    # Update content for each tweet to avoid duplicates
                    if 'content' in params:
                        params['content'] = f'Performance test tweet {i} at {time.time()}'
                    response = self.client.post(endpoint, params)

                elapsed = (time.time() - start) * 1000  # ms
                response_times.append(elapsed)

                # Small delay between requests
                time.sleep(0.1)

            results[description] = {
                'avg_time': f"{statistics.mean(response_times):.2f}ms",
                'min_time': f"{min(response_times):.2f}ms",
                'max_time': f"{max(response_times):.2f}ms",
                'p95_time': f"{statistics.quantiles(response_times, n=20)[18]:.2f}ms"
            }

            print(f"      Avg: {statistics.mean(response_times):.2f}ms")

        self.results['api_response_times'] = results

    def test_fanout_performance(self):
        """Test tweet creation fanout performance"""
        print("\n📤 Testing Tweet Fanout Performance...")

        results = {}

        for user_type, test_user in self.test_users.items():
            if not test_user:
                continue

            follower_count = Friendship.objects.filter(to_user=test_user).count()

            # Skip if using pull model (>5000 followers)
            if follower_count > 5000:
                results[user_type] = {
                    'follower_count': follower_count,
                    'fanout_model': 'pull',
                    'fanout_time': 'N/A (pull model)',
                    'timelines_updated': 0
                }
                continue

            print(f"   Testing {user_type} user ({follower_count} followers)...")

            # Force login
            self.client.force_login(test_user)

            # Create tweet and measure fanout time
            start = time.time()

            response = self.client.post('/api/tweets/', {
                'content': f'Performance test tweet from {user_type}'
            })

            # Wait for async tasks to complete (in real scenario)
            # Since we're using Celery async, the API returns immediately
            api_response_time = (time.time() - start) * 1000

            # In a real test, you'd check Celery task completion
            # For now, we'll measure the immediate response

            results[user_type] = {
                'follower_count': follower_count,
                'fanout_model': 'push',
                'api_response_time': f"{api_response_time:.2f}ms",
                'timelines_updated': follower_count,
                'estimated_async_time': f"{follower_count * 0.5:.0f}ms"  # ~0.5ms per timeline update
            }

            print(f"      API returned in: {api_response_time:.2f}ms")

        self.results['fanout_performance'] = results

    def test_database_performance(self):
        """Test database query performance"""
        print("\n🗄️ Testing Database Performance...")

        queries = []

        # Reset query tracking
        connection.queries_log.clear()

        # Test user with many followers
        celebrity = self.test_users.get('celebrity')
        if celebrity:
            # Timeline query for pull model
            start = time.time()
            following = Friendship.objects.filter(from_user=celebrity).values_list('to_user', flat=True)
            tweets = list(Tweet.objects.filter(
                user__in=following
            ).select_related('user').order_by('-created_at')[:20])
            pull_time = (time.time() - start) * 1000

            queries.append({
                'description': 'Pull model timeline query',
                'time': f"{pull_time:.2f}ms",
                'query_count': len(connection.queries) - len(queries)
            })

        # Test normal user timeline
        normal_user = self.test_users.get('normal')
        if normal_user:
            connection.queries_log.clear()
            start = time.time()

            # Check if user has cached newsfeed
            cache_key = f'newsfeed:{normal_user.id}'
            if not cache.get(cache_key):
                following = Friendship.objects.filter(from_user=normal_user).values_list('to_user', flat=True)
                tweets = list(Tweet.objects.filter(
                    user__in=following
                ).select_related('user').order_by('-created_at')[:20])

            db_time = (time.time() - start) * 1000

            queries.append({
                'description': 'Normal user timeline (no cache)',
                'time': f"{db_time:.2f}ms",
                'query_count': len(connection.queries)
            })

        self.results['database_metrics'] = {
            'queries': queries,
            'index_usage': 'Composite index on (user_id, created_at) for timeline queries'
        }

    def run_load_test(self, concurrent_users=50, duration_seconds=10):
        """Run concurrent user load test"""
        print(f"\n🚀 Running Load Test ({concurrent_users} concurrent users)...")

        # Get test users
        test_users = list(User.objects.filter(
            username__regex=r'^(active_|normal_).*'
        )[:concurrent_users])

        if len(test_users) < concurrent_users:
            print(f"   ⚠️  Only found {len(test_users)} test users")
            concurrent_users = len(test_users)

        results = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'requests_per_second': 0
        }

        def make_request(user):
            """Make a single request as a user"""
            client = Client()
            client.force_login(user)

            start = time.time()
            try:
                # Randomly choose between reading timeline and creating tweet
                if time.time() % 2 < 1.5:  # 75% read, 25% write
                    response = client.get('/api/newsfeeds/')
                else:
                    response = client.post('/api/tweets/', {
                        'content': f'Load test tweet at {time.time()}'
                    })

                elapsed = (time.time() - start) * 1000
                success = response.status_code in [200, 201]

                return {
                    'success': success,
                    'time': elapsed,
                    'status_code': response.status_code
                }
            except Exception as e:
                return {
                    'success': False,
                    'time': (time.time() - start) * 1000,
                    'error': str(e)
                }

        # Run load test
        start_time = time.time()
        end_time = start_time + duration_seconds

        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = []

            while time.time() < end_time:
                for user in test_users:
                    if time.time() >= end_time:
                        break
                    future = executor.submit(make_request, user)
                    futures.append(future)
                    time.sleep(0.1)  # Stagger requests slightly

            # Collect results
            for future in as_completed(futures):
                result = future.result()
                results['total_requests'] += 1

                if result['success']:
                    results['successful_requests'] += 1
                    results['response_times'].append(result['time'])
                else:
                    results['failed_requests'] += 1

        # Calculate metrics
        total_time = time.time() - start_time
        results['requests_per_second'] = results['total_requests'] / total_time

        if results['response_times']:
            results['avg_response_time'] = f"{statistics.mean(results['response_times']):.2f}ms"
            results['p95_response_time'] = f"{statistics.quantiles(results['response_times'], n=20)[18]:.2f}ms"
            results['max_response_time'] = f"{max(results['response_times']):.2f}ms"

        self.results['load_test_results'] = results

        print(f"   ✅ Completed {results['total_requests']} requests")
        print(f"   ✅ Success rate: {(results['successful_requests'] / results['total_requests'] * 100):.1f}%")
        print(f"   ✅ Throughput: {results['requests_per_second']:.1f} req/s")

    def generate_report(self):
        """Generate comprehensive performance report"""
        print("\n" + "=" * 60)
        print("📈 PERFORMANCE TEST REPORT")
        print("=" * 60)

        # Cache Performance
        if self.results['cache_performance']:
            print("\n🔸 Cache Performance:")
            cache_perf = self.results['cache_performance']
            print(f"   • Active users: {cache_perf['active_users']} ({cache_perf['active_user_percentage']:.1f}%)")
            print(f"   • Test sample: {cache_perf['test_sample_size']} users ({cache_perf['active_in_sample']} active)")
            print(f"   • Cache hit rate: {cache_perf['cache_hit_rate']}")
            print(f"   • Avg response time: {cache_perf['avg_response_time']}")
            if cache_perf['p95_response_time'] != "N/A":
                print(f"   • P95 response time: {cache_perf['p95_response_time']}")

        # API Response Times
        if self.results['api_response_times']:
            print("\n🔸 API Response Times:")
            for endpoint, metrics in self.results['api_response_times'].items():
                print(f"   • {endpoint}:")
                print(f"     - Average: {metrics['avg_time']}")
                print(f"     - P95: {metrics['p95_time']}")

        # Fanout Performance
        if self.results['fanout_performance']:
            print("\n🔸 Tweet Fanout Performance:")
            for user_type, metrics in self.results['fanout_performance'].items():
                print(f"   • {user_type} ({metrics['follower_count']} followers):")
                print(f"     - Model: {metrics['fanout_model']}")
                if metrics['fanout_model'] == 'push':
                    print(f"     - API response: {metrics['api_response_time']}")

        # Load Test Results
        if self.results['load_test_results']:
            print("\n🔸 Load Test Results:")
            load_results = self.results['load_test_results']
            print(f"   • Total requests: {load_results['total_requests']}")
            print(
                f"   • Success rate: {(load_results['successful_requests'] / load_results['total_requests'] * 100):.1f}%")
            print(f"   • Throughput: {load_results['requests_per_second']:.1f} req/s")
            if 'avg_response_time' in load_results:
                print(f"   • Avg response time: {load_results['avg_response_time']}")
                print(f"   • P95 response time: {load_results['p95_response_time']}")

        print("\n" + "=" * 60)

        # Save results to file
        with open('performance_test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        print("\n💾 Full results saved to performance_test_results.json")

    def run_all_tests(self):
        """Run all performance tests"""
        print("🏁 Starting Twitter Clone Performance Tests")
        print("=" * 60)

        self.setup_test_users()
        self.test_cache_performance()
        self.test_api_response_times()
        self.test_fanout_performance()
        self.test_database_performance()
        self.run_load_test(concurrent_users=50, duration_seconds=10)
        self.generate_report()


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Run performance tests')
    parser.add_argument('--url', default='http://localhost:8000',
                        help='Base URL for API tests')
    parser.add_argument('--concurrent', type=int, default=50,
                        help='Number of concurrent users for load test')
    parser.add_argument('--duration', type=int, default=10,
                        help='Load test duration in seconds')

    args = parser.parse_args()

    tester = PerformanceTestRunner(base_url=args.url)
    tester.run_all_tests()


if __name__ == '__main__':
    main()