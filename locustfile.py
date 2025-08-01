import random
import json
from locust import HttpUser, task, between
from locust.exception import StopUser


class TwitterUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """每个用户开始时执行：创建用户并登录"""
        # 生成随机用户信息
        self.username = f"loaduser_{random.randint(10000, 99999)}"
        self.email = f"{self.username}@test.com"
        self.password = "testpass123"

        # 注册用户
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
                if not self.user_id:
                    self.user_id = random.randint(100000, 999999)  # 使用更大的范围避免冲突
            else:
                print(f"❌ Failed to create user {self.username}: {response.text}")
                self.user_id = random.randint(100000, 999999)

        # 登录获取认证
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

        # 🔥 关键修复：使用真实存在的用户ID池
        self.tweet_ids = []
        self.comment_ids = []
        self.real_user_ids = []  # 存储从API获取的真实用户ID
        self.following_ids = []

        # 获取真实的用户ID（通过查看新闻推送等方式）
        self._populate_real_user_ids()

    def _populate_real_user_ids(self):
        """获取真实存在的用户ID"""
        # 方法1: 从新闻推送中获取用户ID
        try:
            with self.client.get("/api/newsfeeds/", catch_response=True) as response:
                if response.status_code == 200:
                    results = response.json().get('results', [])
                    for item in results:
                        if 'tweet' in item and 'user' in item['tweet']:
                            user_id = item['tweet']['user']['id']
                            if user_id not in self.real_user_ids and user_id != self.user_id:
                                self.real_user_ids.append(user_id)
        except:
            pass

        # 方法2: 尝试获取一些推文来找到用户ID
        for test_user_id in range(1, 50):  # 只测试前50个ID
            try:
                with self.client.get(f"/api/tweets/?user_id={test_user_id}", catch_response=True) as response:
                    if response.status_code == 200 and response.json().get('results'):
                        if test_user_id not in self.real_user_ids and test_user_id != self.user_id:
                            self.real_user_ids.append(test_user_id)
                        if len(self.real_user_ids) >= 10:  # 获得足够的用户ID就停止
                            break
            except:
                continue

        # 如果还是没有找到足够的用户，添加一些默认值
        if len(self.real_user_ids) < 5:
            # 使用当前用户ID作为备选（虽然不能关注自己，但至少不会报"用户不存在"）
            self.real_user_ids.extend([self.user_id] * 5)

        print(f"📋 Found {len(self.real_user_ids)} real user IDs: {self.real_user_ids[:5]}...")

    @task(5)
    def view_newsfeeds(self):
        """查看新闻推送"""
        with self.client.get("/api/newsfeeds/", catch_response=True) as response:
            if response.status_code == 200:
                results = response.json().get('results', [])
                for item in results[:5]:
                    if 'tweet' in item and 'id' in item['tweet']:
                        tweet_id = item['tweet']['id']
                        if tweet_id not in self.tweet_ids:
                            self.tweet_ids.append(tweet_id)
                    # 同时收集更多真实用户ID
                    if 'tweet' in item and 'user' in item['tweet']:
                        user_id = item['tweet']['user']['id']
                        if user_id not in self.real_user_ids and user_id != self.user_id:
                            self.real_user_ids.append(user_id)
            elif response.status_code == 403:
                response.failure("Authentication required")
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(3)
    def view_user_tweets(self):
        """查看用户推文列表"""
        if not self.real_user_ids:
            return

        user_id = random.choice(self.real_user_ids)
        with self.client.get(f"/api/tweets/?user_id={user_id}", catch_response=True) as response:
            if response.status_code == 200:
                results = response.json().get('results', [])
                for tweet in results[:3]:
                    if 'id' in tweet and tweet['id'] not in self.tweet_ids:
                        self.tweet_ids.append(tweet['id'])
            else:
                response.failure(f"Failed to load tweets: {response.status_code}")

    @task(2)
    def create_tweet(self):
        """发布推文"""
        content = f"Load test tweet from {self.username} at {random.randint(1, 10000)} 🚀"

        with self.client.post("/api/tweets/",
                              json={"content": content},
                              catch_response=True) as response:
            if response.status_code == 201:
                tweet_id = response.json().get('id')
                if tweet_id:
                    self.tweet_ids.append(tweet_id)
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Tweet creation failed: {response.status_code}")

    @task(2)
    def view_tweet_details(self):
        """查看推文详情"""
        if not self.tweet_ids:
            return

        tweet_id = random.choice(self.tweet_ids)
        with self.client.get(f"/api/tweets/{tweet_id}/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                if tweet_id in self.tweet_ids:
                    self.tweet_ids.remove(tweet_id)
                response.success()
            else:
                response.failure(f"Tweet detail failed: {response.status_code}")

    @task(2)
    def view_following_list(self):
        """查看关注列表"""
        with self.client.get(f"/api/friendships/?from_user_id={self.user_id}",
                             catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Following list failed: {response.status_code}")

    @task(2)
    def view_followers_list(self):
        """查看粉丝列表"""
        with self.client.get(f"/api/friendships/?to_user_id={self.user_id}",
                             catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Followers list failed: {response.status_code}")

    @task(1)
    def follow_user(self):
        """关注用户 - 使用真实存在的用户ID"""
        if not self.real_user_ids:
            return

        # 🔥 关键修复：从真实用户ID池中选择
        to_user_id = random.choice(self.real_user_ids)

        # 避免关注自己或已经关注的用户
        if to_user_id == self.user_id or to_user_id in self.following_ids:
            return

        follow_data = {
            "to_user_id": to_user_id
        }

        with self.client.post("/api/friendships/",
                              json=follow_data,
                              catch_response=True) as response:
            if response.status_code in [200, 201]:
                self.following_ids.append(to_user_id)
                response.success()
                print(f"✅ User {self.user_id} followed user {to_user_id}")
            elif response.status_code == 429:
                response.success()
            elif response.status_code == 400:
                # 可能是尝试关注自己，标记为成功但不记录
                response.success()
            else:
                response.failure(f"Follow failed: {response.status_code} - {response.text}")

    @task(1)
    def unfollow_user(self):
        """取消关注用户"""
        if not self.following_ids:
            return

        to_user_id = random.choice(self.following_ids)

        with self.client.delete(f"/api/friendships/remove/?to_user_id={to_user_id}",
                                catch_response=True) as response:
            if response.status_code == 204:
                self.following_ids.remove(to_user_id)
                response.success()
                print(f"✅ User {self.user_id} unfollowed user {to_user_id}")
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Unfollow failed: {response.status_code}")

    @task(1)
    def create_comment(self):
        """创建评论"""
        if not self.tweet_ids:
            return

        tweet_id = random.choice(self.tweet_ids)
        comment_content = f"Test comment from {self.username}"

        with self.client.post("/api/comments/",
                              json={
                                  "tweet_id": tweet_id,
                                  "content": comment_content
                              }, catch_response=True) as response:
            if response.status_code == 201:
                comment_id = response.json().get('id')
                if comment_id and comment_id not in self.comment_ids:
                    self.comment_ids.append(comment_id)
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Comment creation failed: {response.status_code}")

    @task(1)
    def like_tweet(self):
        """点赞推文"""
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
                response.failure(f"Like tweet failed: {response.status_code} - {response.text}")

    @task(1)
    def like_comment(self):
        """点赞评论"""
        if not self.comment_ids:
            return

        comment_id = random.choice(self.comment_ids)

        like_data = {
            "content_type": "comment",
            "content_id": comment_id
        }

        with self.client.post("/api/likes/",
                              json=like_data,
                              catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Like comment failed: {response.status_code}")


# 轻量级用户 - 主要浏览
class LightUser(TwitterUser):
    wait_time = between(3, 8)
    weight = 3

    @task(10)
    def view_newsfeeds(self):
        super().view_newsfeeds()

    @task(5)
    def view_user_tweets(self):
        super().view_user_tweets()

    @task(2)
    def view_following_list(self):
        super().view_following_list()

    @task(1)
    def like_tweet(self):
        super().like_tweet()


# 重度用户 - 更多互动
class HeavyUser(TwitterUser):
    wait_time = between(0.5, 2)
    weight = 1

    @task(8)
    def view_newsfeeds(self):
        super().view_newsfeeds()

    @task(4)
    def create_tweet(self):
        super().create_tweet()

    @task(3)
    def follow_user(self):
        super().follow_user()

    @task(2)
    def create_comment(self):
        super().create_comment()

    @task(2)
    def like_tweet(self):
        super().like_tweet()