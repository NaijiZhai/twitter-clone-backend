#!/usr/bin/env python
"""
Realistic Test Data Setup Script for Performance Testing

This script creates a realistic test dataset based on real social network patterns:
- Power-law distribution for follower counts
- Realistic user activity patterns
- Time-based user behavior simulation
"""

import os
import sys
import random
import math
from datetime import datetime, timedelta
from collections import defaultdict

# Setup Django environment FIRST
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'twitter.settings')

import django

django.setup()

# Now import Django models after setup
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from friendships.models import Friendship
from tweets.models import Tweet


class RealisticTestDataSetup:
    """Create realistic test data based on real social network patterns"""

    def __init__(self):
        self.users_by_category = {
            'celebrity': [],  # >5000 followers (top 1%)
            'influencer': [],  # 1000-5000 followers (4%)
            'active': [],  # 100-1000 followers (15%)
            'normal': [],  # 10-100 followers (30%)
            'lurker': []  # <10 followers (50%)
        }
        self.all_users = []
        self.user_activity_pattern = {}  # Track when users are active

    def create_realistic_user_distribution(self, total_users=10000):
        """Create users following real social network distribution"""
        print(f"Creating {total_users} users with realistic distribution...")

        # Realistic distribution based on Twitter/social media data
        distribution = {
            'celebrity': int(total_users * 0.001),  # 0.1% - very rare
            'influencer': int(total_users * 0.04),  # 4%
            'active': int(total_users * 0.15),  # 15%
            'normal': int(total_users * 0.30),  # 30%
            'lurker': int(total_users * 0.509)  # 50.9%
        }

        # Ensure we have at least some celebrities for testing
        distribution['celebrity'] = max(5, distribution['celebrity'])

        users_created = 0

        with transaction.atomic():
            for category, count in distribution.items():
                for i in range(count):
                    username = f'{category}_{i}_{random.randint(1000, 9999)}'

                    if not User.objects.filter(username=username).exists():
                        user = User.objects.create_user(
                            username=username,
                            email=f'{username}@test.com',
                            password='testpass123',
                            first_name=category.capitalize(),
                            last_name=f'User{i}'
                        )

                        # Set user activity pattern
                        self._set_user_activity_pattern(user, category)

                        self.users_by_category[category].append(user)
                        self.all_users.append(user)
                        users_created += 1

        print(f"✅ Created {users_created} users with distribution:")
        for category, users in self.users_by_category.items():
            print(f"   • {category}: {len(users)} users")

    def _set_user_activity_pattern(self, user, category):
        """Set realistic activity patterns based on user type"""
        now = timezone.now()

        if category == 'celebrity':
            # Celebrities are very active, multiple times daily
            last_login = now - timedelta(hours=random.randint(1, 6))
            posts_per_day = random.uniform(3, 10)
            active_hours = list(range(24))  # Active any time

        elif category == 'influencer':
            # Influencers post regularly, daily active
            last_login = now - timedelta(hours=random.randint(1, 24))
            posts_per_day = random.uniform(1, 5)
            active_hours = list(range(8, 23))  # Active during day/evening

        elif category == 'active':
            # Active users check daily, post occasionally
            last_login = now - timedelta(hours=random.randint(1, 48))
            posts_per_day = random.uniform(0.3, 2)
            active_hours = [8, 9, 12, 13, 17, 18, 19, 20, 21, 22]  # Peak hours

        elif category == 'normal':
            # Normal users check every few days
            last_login = now - timedelta(days=random.randint(1, 7))
            posts_per_day = random.uniform(0.1, 0.5)
            active_hours = [12, 18, 19, 20, 21]  # Lunch and evening

        else:  # lurker
            # Lurkers rarely post, check occasionally
            last_login = now - timedelta(days=random.randint(7, 30))
            posts_per_day = random.uniform(0, 0.1)
            active_hours = [19, 20, 21]  # Brief evening check

        self.user_activity_pattern[user.id] = {
            'last_login': last_login,
            'posts_per_day': posts_per_day,
            'active_hours': active_hours,
            'category': category
        }

    def create_realistic_social_graph(self):
        """Create social connections following real patterns"""
        print("Building realistic social network...")

        friendships_to_create = []

        # 1. Celebrities follow each other (small world effect)
        celebrities = self.users_by_category['celebrity']
        for i, celeb in enumerate(celebrities):
            # Each celebrity follows 30-70% of other celebrities
            other_celebs = celebrities[:i] + celebrities[i + 1:]
            follow_count = int(len(other_celebs) * random.uniform(0.3, 0.7))
            to_follow = random.sample(other_celebs, follow_count)

            for target in to_follow:
                friendships_to_create.append(self._create_friendship(celeb, target))

        # 2. Create follower relationships based on power law
        for category, users in self.users_by_category.items():
            if category == 'celebrity':
                # Celebrities get 5000-50000 followers
                self._assign_followers(users, friendships_to_create,
                                       min_followers=5000, max_followers=50000)

            elif category == 'influencer':
                # Influencers get 1000-5000 followers
                self._assign_followers(users, friendships_to_create,
                                       min_followers=1000, max_followers=5000)

            elif category == 'active':
                # Active users get 100-1000 followers
                self._assign_followers(users, friendships_to_create,
                                       min_followers=100, max_followers=1000)

        # 3. Normal social connections (friends following friends)
        for user in self.all_users:
            # Follow 5-50 users based on activity level
            pattern = self.user_activity_pattern[user.id]
            if pattern['category'] == 'lurker':
                follow_count = random.randint(5, 20)
            elif pattern['category'] == 'normal':
                follow_count = random.randint(10, 50)
            else:
                follow_count = random.randint(20, 100)

            # Mix of following different user types
            targets = self._select_follow_targets(user, follow_count)
            for target in targets:
                if target != user:
                    friendships_to_create.append(self._create_friendship(user, target))

        # Batch create with progress indicator
        if friendships_to_create:
            print(f"Creating {len(friendships_to_create)} friendships...")
            batch_size = 5000
            for i in range(0, len(friendships_to_create), batch_size):
                batch = friendships_to_create[i:i + batch_size]
                Friendship.objects.bulk_create(batch, ignore_conflicts=True)
                print(f"   Progress: {min(i + batch_size, len(friendships_to_create))}/{len(friendships_to_create)}")

        print(f"✅ Created social network with {len(friendships_to_create)} connections")

    def _assign_followers(self, users, friendships_list, min_followers, max_followers):
        """Assign followers to users using realistic distribution"""
        potential_followers = [u for u in self.all_users if u not in users]

        for user in users:
            # Use log-normal distribution for more realistic follower counts
            follower_count = int(random.lognormvariate(
                math.log((min_followers + max_followers) / 2),
                0.5
            ))
            follower_count = max(min_followers, min(follower_count, max_followers))

            # Select followers with bias towards active users
            followers = self._weighted_sample(potential_followers, follower_count)

            for follower in followers:
                friendships_list.append(self._create_friendship(follower, user))

    def _weighted_sample(self, users, count):
        """Sample users with weight bias towards active users"""
        if len(users) <= count:
            return users

        # Weight by activity level
        weights = []
        for user in users:
            pattern = self.user_activity_pattern[user.id]
            category_weights = {
                'celebrity': 5,
                'influencer': 4,
                'active': 3,
                'normal': 2,
                'lurker': 1
            }
            weights.append(category_weights.get(pattern['category'], 1))

        return random.choices(users, weights=weights, k=count)

    def _select_follow_targets(self, user, count):
        """Select who a user should follow based on realistic patterns"""
        targets = []

        # 60% follow popular accounts
        popular_users = (self.users_by_category['celebrity'] +
                         self.users_by_category['influencer'])
        popular_count = int(count * 0.6)
        if popular_users:
            targets.extend(random.sample(
                popular_users,
                min(popular_count, len(popular_users))
            ))

        # 40% follow regular users (social connections)
        regular_users = [u for u in self.all_users if u not in popular_users and u != user]
        regular_count = count - len(targets)
        if regular_users and regular_count > 0:
            targets.extend(random.sample(
                regular_users,
                min(regular_count, len(regular_users))
            ))

        return targets

    def _create_friendship(self, from_user, to_user):
        """Create a friendship with realistic timestamp"""
        # Older accounts have older connections
        days_ago = random.randint(1, 365)
        created_at = timezone.now() - timedelta(days=days_ago)

        return Friendship(
            from_user=from_user,
            to_user=to_user,
            created_at=created_at
        )

    def create_realistic_tweets(self):
        """Create tweets based on user activity patterns"""
        print("Creating realistic tweet distribution...")

        tweets_to_create = []
        now = timezone.now()

        for user in self.all_users:
            pattern = self.user_activity_pattern[user.id]

            # Calculate tweets for last 30 days based on posts_per_day
            total_tweets = int(pattern['posts_per_day'] * 30)

            for _ in range(total_tweets):
                # Distribute tweets realistically over time
                days_ago = random.randint(0, 30)
                hour = random.choice(pattern['active_hours'])
                minute = random.randint(0, 59)

                tweet_time = now - timedelta(days=days_ago, hours=now.hour - hour, minutes=minute)

                content = self._generate_realistic_content(user, pattern['category'])

                tweets_to_create.append(Tweet(
                    user=user,
                    content=content,
                    created_at=tweet_time
                ))

        # Batch create tweets
        if tweets_to_create:
            print(f"Creating {len(tweets_to_create)} tweets...")
            Tweet.objects.bulk_create(tweets_to_create, batch_size=1000)

        print(f"✅ Created {len(tweets_to_create)} tweets with realistic distribution")

    def _generate_realistic_content(self, user, category):
        """Generate content based on user type"""
        if category == 'celebrity':
            templates = [
                "Excited to announce my new project! Stay tuned for more details 🎉",
                "Thank you for all the love and support! You guys are amazing ❤️",
                "Behind the scenes from today's shoot 📸",
                "Can't wait to share what we've been working on!",
                "Grateful for this incredible journey 🙏",
            ]
        elif category == 'influencer':
            templates = [
                "5 tips for better productivity! Thread below 👇",
                "Just posted a new video! Link in bio 🎥",
                "What's your favorite morning routine?",
                "Collaboration announcement coming soon!",
                "Today's motivation: You've got this! 💪",
            ]
        else:
            templates = [
                "Great weekend with family and friends!",
                "Anyone watching the game tonight?",
                "Coffee thoughts ☕",
                "New restaurant in town is amazing!",
                "Monday mood 😅",
                "Weekend vibes 🌟",
                "Just finished a great book!",
                "Beautiful weather today!"
            ]

        content = random.choice(templates)

        # Add hashtags based on user type
        if category in ['celebrity', 'influencer']:
            hashtags = ['#blessed', '#motivation', '#lifestyle', '#instagood', '#photooftheday']
            if random.random() < 0.7:  # 70% chance of hashtags
                content += f" {random.choice(hashtags)}"

        return content[:255]

    def simulate_24h_activity(self):
        """Simulate realistic 24-hour user activity for cache testing"""
        print("\nSimulating 24-hour user activity...")

        active_users = []
        now = timezone.now()

        for user in self.all_users:
            pattern = self.user_activity_pattern[user.id]

            # Check if user would have logged in within 24 hours
            hours_since_login = (now - pattern['last_login']).total_seconds() / 3600

            if hours_since_login <= 24:
                active_users.append(user)
                # Update last login to simulate activity
                user.last_login = pattern['last_login']
                user.save(update_fields=['last_login'])

        print(
            f"✅ {len(active_users)} users ({len(active_users) / len(self.all_users) * 100:.1f}%) active in last 24 hours")

        # Category breakdown
        category_activity = defaultdict(int)
        for user in active_users:
            category = self.user_activity_pattern[user.id]['category']
            category_activity[category] += 1

        print("   Activity by user type:")
        for category, count in category_activity.items():
            total_in_category = len(self.users_by_category[category])
            percentage = (count / total_in_category * 100) if total_in_category > 0 else 0
            print(f"   • {category}: {count}/{total_in_category} ({percentage:.1f}%)")

        return active_users

    def print_performance_metrics(self):
        """Print metrics relevant for performance testing"""
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE TEST METRICS")
        print("=" * 60)

        # User distribution
        total_users = len(self.all_users)
        print(f"\n👥 User Distribution ({total_users} total):")
        for category, users in self.users_by_category.items():
            print(f"   • {category}: {len(users)} ({len(users) / total_users * 100:.1f}%)")

        # Follower distribution
        print(f"\n📈 Follower Count Distribution:")
        follower_counts = defaultdict(list)

        for category, users in self.users_by_category.items():
            for user in users[:min(5, len(users))]:  # Sample up to 5 users per category
                count = Friendship.objects.filter(to_user=user).count()
                follower_counts[category].append(count)

        for category, counts in follower_counts.items():
            if counts:
                avg = sum(counts) / len(counts)
                print(f"   • {category}: avg {avg:.0f} followers (sample: {counts})")

        # Activity metrics
        print(f"\n⚡ Activity Patterns:")
        total_tweets = Tweet.objects.count()
        tweets_24h = Tweet.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count()

        print(f"   • Total tweets: {total_tweets}")
        print(f"   • Tweets in last 24h: {tweets_24h}")
        print(f"   • Average tweets per user: {total_tweets / total_users:.1f}")

        # Cache simulation metrics
        active_users = self.simulate_24h_activity()

        print(f"\n💾 Cache Optimization Metrics:")
        print(f"   • Active users (24h): {len(active_users)}")
        print(f"   • Cache size estimate: ~{len(active_users) * 500 / 1024:.1f} KB")
        print(f"   • Expected cache hit rate: ~{len(active_users) / total_users * 100:.1f}%")

        # Performance test recommendations
        print(f"\n🚀 Performance Test Scenarios:")
        print(
            f"   • Celebrity tweet (push to {Friendship.objects.filter(to_user__in=self.users_by_category['celebrity']).count()} timelines)")
        print(f"   • Normal user tweet (push to <100 timelines)")
        print(f"   • Pull model queries (for {len(self.users_by_category['celebrity'])} celebrity accounts)")
        print(f"   • Cache warmup for {len(active_users)} active users")

        print("=" * 60)

    def cleanup_test_data(self):
        """Clean up all test data"""
        print("⚠️  Cleaning up test data...")

        # Delete in correct order to avoid foreign key issues
        Tweet.objects.filter(user__in=self.all_users).delete()
        Friendship.objects.filter(from_user__in=self.all_users).delete()
        Friendship.objects.filter(to_user__in=self.all_users).delete()

        for prefix in ['celebrity_', 'influencer_', 'active_', 'normal_', 'lurker_']:
            User.objects.filter(username__startswith=prefix).delete()

        print("✅ Cleanup completed")

    def run_setup(self, total_users=10000, clean_first=True):
        """Run the complete realistic test data setup"""
        print("🚀 Setting up realistic test data for performance testing...\n")

        if clean_first:
            self.cleanup_test_data()

        # Create test data
        self.create_realistic_user_distribution(total_users)
        self.create_realistic_social_graph()
        self.create_realistic_tweets()

        # Print metrics
        self.print_performance_metrics()

        print(f"\n✅ Realistic test data setup completed!")
        print(f"\n📝 Next steps:")
        print(f"   1. Run performance tests: python manage.py test_performance")
        print(f"   2. Monitor cache hit rates during testing")
        print(f"   3. Test celebrity tweet fanout performance")
        print(f"   4. Verify pull model efficiency for high-follower accounts")


def main():
    """Main function to run the setup"""
    import argparse

    parser = argparse.ArgumentParser(description='Setup realistic test data')
    parser.add_argument('--users', type=int, default=10000,
                        help='Total number of users to create (default: 10000)')
    parser.add_argument('--no-cleanup', action='store_true',
                        help='Skip cleanup of existing test data')

    args = parser.parse_args()

    setup = RealisticTestDataSetup()
    setup.run_setup(total_users=args.users, clean_first=not args.no_cleanup)


if __name__ == '__main__':
    main()