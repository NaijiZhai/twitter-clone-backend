from django.test import TestCase

# Create your tests here.
from testing.testcases import TestCase
from rest_framework.test import APIClient

from tweets.models import Tweet

COMMENT_URL = '/api/comments/'


class CommentApiTests(TestCase):

    def setUp(self):
        self.zhai = self.create_user('zhai')
        self.zhai_client = APIClient()
        self.zhai_client.force_authenticate(self.zhai)
        self.zhou = self.create_user('zhou')
        self.zhou_client = APIClient()
        self.zhou_client.force_authenticate(self.zhou)

        self.tweet = self.create_tweet(self.zhai)

    def test_create(self):
        # log in
        response = self.anonymous_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, 403)

        # args
        response = self.zhai_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, 400)

        # content
        response = self.zhai_client.post(COMMENT_URL, {'tweet_id': self.tweet.id})
        self.assertEqual(response.status_code, 400)

        # tweet_id
        response = self.zhai_client.post(COMMENT_URL, {'content': '1'})
        self.assertEqual(response.status_code, 400)

        # content len <= 140
        response = self.zhai_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1' * 141,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual('content' in response.data['errors'], True)

        # both tweet_id user_id
        response = self.zhai_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['user']['id'], self.zhai.id)
        self.assertEqual(response.data['tweet']['id'], self.tweet.id)
        self.assertEqual(response.data['content'], '1')
