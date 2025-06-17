from notifications.models import Notification
from testing.testcases import TestCase


COMMENT_URL = '/api/comments/'
LIKE_URL = '/api/likes/'


class NotificationTests(TestCase):

    def setUp(self):
        self.zhai, self.zhai_client = self.create_user_and_client('zhai')
        self.zhou, self.zhou_client = self.create_user_and_client('dong')
        self.zhou_tweet = self.create_tweet(self.zhou)

    def test_comment_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        self.zhai_client.post(COMMENT_URL, {
            'tweet_id': self.zhou_tweet.id,
            'content': 'ayo ayo',
        })
        self.assertEqual(Notification.objects.count(), 1)

    def test_like_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        self.zhai_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'content_id': self.zhou_tweet.id,
        })
        self.assertEqual(Notification.objects.count(), 1)
