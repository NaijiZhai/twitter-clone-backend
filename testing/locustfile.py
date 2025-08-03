import random
import json
import time
from locust import HttpUser, task, between
from locust.exception import StopUser

# High follower users from your performance test - these are the users that should trigger pull model
HIGH_FOLLOWER_USERS = [
    112948, 112951, 112954, 112955, 112947, 112953, 112949, 112950, 112952, 112956,
    113346, 113189, 113062, 113224, 113010, 113351, 112998, 113231, 113101, 113261,
]


class TwitterUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Execute when each user starts: create user and login"""
        # Generate random user information
        self.username = f"loaduser_{random.randint(10000, 99999)}"
        self.email = f"{self.username}@test.com"
        self.password = "testpass123"
        self.request_count = 0  # Track request count for performance testing

        # Register user
        signup_data = {
            "username": self.username,
            "email": self.email,
            "password": self.password
        }

        with self.client.post("/api/accounts/signup/", json=signup_data, catch_response=True) as response:
            if response.status_code == 201:
                print(f"✅ User {self.username} created successfully")
                user_data = response.json().get('user', {})
                self.user_id = user_data.get('id')
            else:
                print(f"❌ Failed to create user {self.username}: {response.text}")
                # Still continue with a dummy ID for testing
                self.user_id = random.randint(100000, 999999)

        # Login to get authentication
        login_data = {
            "username": self.username,
            "password": self.password
        }

        with self.client.post("/api/accounts/login/", json=login_data, catch_response=True) as response:
            if response.status_code == 200:
                token = response.json().get('token')
                if token:
                    self.client.headers = {
                        'Authorization': f'Token {token}',
                        'Content-Type': 'application/json'
                    }
                print(f"✅ User {self.username} logged in successfully")
            else:
                print(f"❌ Login failed for {self.username}: {response.text}")

        # Initialize data structures
        self.tweet_ids = []
        self.comment_ids = []
        self.following_ids = []

        # 🔥 KEY: Follow high-follower users to create pressure test scenario
        self._follow_high_follower_users()

    def _follow_high_follower_users(self):
        """Follow the high-follower users to trigger pull model and stress test the system"""
        print(f"🎯 Setting up pressure test: following high-follower users...")

        # Follow a random subset of high-follower users (5-15 users per test user)
        num_to_follow = random.randint(5, 15)
        users_to_follow = random.sample(HIGH_FOLLOWER_USERS, min(num_to_follow, len(HIGH_FOLLOWER_USERS)))

        successful_follows = 0
        for user_id in users_to_follow:
            try:
                follow_data = {"to_user_id": user_id}

                with self.client.post("/api/friendships/",
                                      json=follow_data,
                                      catch_response=True) as response:
                    if response.status_code in [200, 201]:
                        self.following_ids.append(user_id)
                        successful_follows += 1
                        print(f"✅ {self.username} followed high-follower user {user_id}")
                    elif response.status_code == 400:
                        # User might not exist or already following
                        print(f"⚠️  Could not follow user {user_id} (might not exist)")
                    else:
                        print(f"❌ Failed to follow user {user_id}: {response.status_code}")

                # Small delay to avoid overwhelming the server during setup
                time.sleep(0.1)

            except Exception as e:
                print(f"❌ Exception following user {user_id}: {e}")

        print(f"🔥 Pressure test setup complete: {self.username} follows {successful_follows} high-follower users")
        print(f"📊 This should trigger pull model for newsfeeds (users with ≥5000 followers)")

        if successful_follows == 0:
            print(f"⚠️  WARNING: {self.username} is not following any high-follower users!")

    @task(10)  # Highest priority - this is what we want to stress test
    def view_newsfeeds_stress_test(self):
        """Main stress test: View newsfeeds from high-follower users (pull model)"""
        start_time = time.time()

        with self.client.get("/api/newsfeeds/", catch_response=True) as response:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to ms

            self.request_count += 1

            if response.status_code == 200:
                results = response.json().get('results', [])
                tweet_count = len(results)

                # This should be testing pull model performance since we follow high-follower users
                cache_indicator = "🔥" if self.request_count > 1 else "❄️"
                model_type = "PULL" if any(fid in HIGH_FOLLOWER_USERS for fid in self.following_ids) else "PUSH"

                print(
                    f"[{self.username}] {model_type} Model Request {self.request_count}: {response_time:.2f}ms | {tweet_count} tweets | {cache_indicator}")

                # Collect tweet IDs for other operations
                for item in results[:5]:
                    if 'tweet' in item and 'id' in item['tweet']:
                        tweet_id = item['tweet']['id']
                        if tweet_id not in self.tweet_ids:
                            self.tweet_ids.append(tweet_id)

                # Performance assessment
                if response_time > 200:
                    print(f"⚠️  SLOW RESPONSE: {response_time:.2f}ms for {model_type} model")
                elif response_time < 100:
                    print(f"🚀 FAST RESPONSE: {response_time:.2f}ms for {model_type} model")

            elif response.status_code == 403:
                response.failure("Authentication required")
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(5)
    def view_newsfeeds_pull_refresh_stress(self):
        """Stress test pull-to-refresh (should always hit DB for high-follower users)"""
        params = {"created_at_gt": "2025-08-01T00:00:00Z"}
        start_time = time.time()

        with self.client.get("/api/newsfeeds/", params=params, catch_response=True) as response:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000

            if response.status_code == 200:
                tweet_count = len(response.json().get('results', []))
                print(f"[{self.username}] PULL-REFRESH (DB): {response_time:.2f}ms | {tweet_count} tweets | 🔄")

                if response_time > 300:
                    print(f"⚠️  SLOW DB QUERY: {response_time:.2f}ms for pull-refresh")
            else:
                response.failure(f"Pull refresh failed: {response.status_code}")

    @task(5)
    def view_newsfeeds_infinite_scroll_stress(self):
        """Stress test infinite scroll (cache + DB fallback for high-follower users)"""
        params = {"created_at_lt": "2025-08-01T00:00:00Z"}
        start_time = time.time()

        with self.client.get("/api/newsfeeds/", params=params, catch_response=True) as response:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000

            if response.status_code == 200:
                tweet_count = len(response.json().get('results', []))
                print(f"[{self.username}] INFINITE-SCROLL: {response_time:.2f}ms | {tweet_count} tweets | 📜")
            else:
                response.failure(f"Infinite scroll failed: {response.status_code}")

    @task(3)
    def view_newsfeeds_large_page_stress(self):
        """Stress test large page size (more data = more pressure on pull model)"""
        params = {"count": 50}
        start_time = time.time()

        with self.client.get("/api/newsfeeds/", params=params, catch_response=True) as response:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000

            if response.status_code == 200:
                tweet_count = len(response.json().get('results', []))
                print(f"[{self.username}] LARGE-PAGE (50): {response_time:.2f}ms | {tweet_count} tweets | 📄")

                if response_time > 500:
                    print(f"⚠️  SLOW LARGE PAGE: {response_time:.2f}ms for 50 tweets")
            else:
                response.failure(f"Large page failed: {response.status_code}")

    @task(2)
    def create_tweet_by_high_follower_user(self):
        """Create tweets to generate content for high-follower users"""
        content = f"Stress test tweet from {self.username} #{random.randint(1, 10000)} 🔥 Testing hybrid push/pull system"

        with self.client.post("/api/tweets/",
                              json={"content": content},
                              catch_response=True) as response:
            if response.status_code == 201:
                tweet_id = response.json().get('id')
                if tweet_id:
                    self.tweet_ids.append(tweet_id)
                print(f"📝 {self.username} created tweet {tweet_id} (followers will get via pull model)")
                response.success()
            elif response.status_code == 429:
                response.success()  # Rate limit is OK during stress test
            else:
                response.failure(f"Tweet creation failed: {response.status_code}")

    @task(2)
    def like_tweets_from_high_followers(self):
        """Like tweets to generate activity"""
        if not self.tweet_ids:
            return

        tweet_id = random.choice(self.tweet_ids)
        like_data = {
            "content_type": "tweet",
            "content_id": tweet_id
        }

        with self.client.post("/api/likes/",
                              json=like_data,
                              catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Like tweet failed: {response.status_code}")

    @task(1)
    def follow_more_high_follower_users(self):
        """Occasionally follow more high-follower users to increase pressure"""
        if len(self.following_ids) >= 15:  # Don't follow too many
            return

        available_users = [uid for uid in HIGH_FOLLOWER_USERS if uid not in self.following_ids]
        if not available_users:
            return

        user_to_follow = random.choice(available_users)
        follow_data = {"to_user_id": user_to_follow}

        with self.client.post("/api/friendships/",
                              json=follow_data,
                              catch_response=True) as response:
            if response.status_code in [200, 201]:
                self.following_ids.append(user_to_follow)
                print(f"🎯 {self.username} now follows {len(self.following_ids)} high-follower users")
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Follow failed: {response.status_code}")

    @task(1)
    def view_high_follower_user_tweets(self):
        """View tweets from specific high-follower users"""
        if not self.following_ids:
            return

        user_id = random.choice(self.following_ids)
        with self.client.get(f"/api/tweets/?user_id={user_id}", catch_response=True) as response:
            if response.status_code == 200:
                results = response.json().get('results', [])
                print(f"📋 Viewing {len(results)} tweets from high-follower user {user_id}")
                for tweet in results[:3]:
                    if 'id' in tweet and tweet['id'] not in self.tweet_ids:
                        self.tweet_ids.append(tweet['id'])
            else:
                response.failure(f"Failed to load user tweets: {response.status_code}")


# Light stress user - focuses on read operations
class LightStressUser(TwitterUser):
    wait_time = between(2, 5)
    weight = 4  # Most users are light users

    @task(15)
    def view_newsfeeds_stress_test(self):
        super().view_newsfeeds_stress_test()

    @task(5)
    def view_newsfeeds_pull_refresh_stress(self):
        super().view_newsfeeds_pull_refresh_stress()

    @task(3)
    def view_newsfeeds_infinite_scroll_stress(self):
        super().view_newsfeeds_infinite_scroll_stress()

    @task(1)
    def like_tweets_from_high_followers(self):
        super().like_tweets_from_high_followers()


# Heavy stress user - creates more load
class HeavyStressUser(TwitterUser):
    wait_time = between(0.5, 2)
    weight = 1  # Fewer heavy users

    @task(12)
    def view_newsfeeds_stress_test(self):
        super().view_newsfeeds_stress_test()

    @task(6)
    def view_newsfeeds_pull_refresh_stress(self):
        super().view_newsfeeds_pull_refresh_stress()

    @task(4)
    def view_newsfeeds_infinite_scroll_stress(self):
        super().view_newsfeeds_infinite_scroll_stress()

    @task(3)
    def view_newsfeeds_large_page_stress(self):
        super().view_newsfeeds_large_page_stress()

    @task(3)
    def create_tweet_by_high_follower_user(self):
        super().create_tweet_by_high_follower_user()

    @task(2)
    def follow_more_high_follower_users(self):
        super().follow_more_high_follower_users()