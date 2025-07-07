from django.contrib.contenttypes.models import ContentType

from cache_utils.cache_constants import USER_TWEETS_PATTERN
from likes.models import Like
from testing.testcases import TestCase
from tweets.constants import TweetPhotoStatus
from tweets.models import TweetPhoto
from cache_utils.redis_client import RedisClient
from cache_utils.redis_serializer import RedisSerializer
from tweets.services import TweetService


class TweetTests(TestCase):

    def setUp(self):
        self.zhai = self.create_user('zhai')
        self.tweet = self.create_tweet(self.zhai)

    def test_like(self):
        user = self.create_user('user1')
        tweet = self.create_tweet(user=user)
        self.create_like(user=user, target=tweet)
        like = Like.objects.filter(content_type=ContentType.objects.get_for_model(tweet.__class__), content_id=tweet.id).first()
        self.assertNotEquals(like, None)
    
    def test_create_photo(self):
        photo = TweetPhoto.objects.create(
            tweet=self.tweet,
            user=self.zhai,
        )
        self.assertEqual(photo.user, self.zhai)
        self.assertEqual(photo.status, TweetPhotoStatus.PENDING)
        self.assertEqual(self.tweet.tweetphoto_set.count(), 1)


class TweetServiceTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.zhai = self.create_user('zhai')

    def test_get_user_tweets(self):
        tweet_ids = []
        for i in range(3):
            tweet = self.create_tweet(self.zhai, 'tweet {}'.format(i))
            tweet_ids.append(tweet.id)
        tweet_ids = tweet_ids[::-1]

        RedisClient.clear()
        conn = RedisClient.get_connection()

        # cache miss
        tweets = TweetService.get_cached_tweets(self.zhai.id)
        self.assertEqual([t.id for t in tweets], tweet_ids)

        # cache hit
        tweets = TweetService.get_cached_tweets(self.zhai.id)
        self.assertEqual([t.id for t in tweets], tweet_ids)

        # cache updated
        new_tweet = self.create_tweet(self.zhai, 'new tweet')
        tweets = TweetService.get_cached_tweets(self.zhai.id)
        tweet_ids.insert(0, new_tweet.id)
        self.assertEqual([t.id for t in tweets], tweet_ids)

    def test_create_new_tweet_before_get_cached_tweets(self):
        tweet1 = self.create_tweet(self.zhai, 'tweet1')

        RedisClient.clear()
        conn = RedisClient.get_connection()

        key = USER_TWEETS_PATTERN.format(user_id=self.zhai.id)
        self.assertEqual(conn.exists(key), False)
        tweet2 = self.create_tweet(self.zhai, 'tweet2')
        self.assertEqual(conn.exists(key), True)

        tweets = TweetService.get_cached_tweets(self.zhai.id)
        self.assertEqual([t.id for t in tweets], [tweet2.id, tweet1.id])
