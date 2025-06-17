from notifications.models import Notification
from testing.testcases import TestCase

COMMENT_URL = '/api/comments/'
LIKE_URL = '/api/likes/'
NOTIFICATION_URL = '/api/notifications/'


class NotificationTests(TestCase):

    def setUp(self):
        self.zhai, self.zhai_client = self.create_user_and_client('zhai')
        self.zhou, self.zhou_client = self.create_user_and_client('dong')
        self.zhou_tweet = self.create_tweet(self.zhou)

    def test_comment_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        self.zhai_client.post(COMMENT_URL, {
            'tweet_id': self.zhou_tweet.id,
            'content': 'a ha',
        })
        self.assertEqual(Notification.objects.count(), 1)

    def test_like_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        self.zhai_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'content_id': self.zhou_tweet.id,
        })
        self.assertEqual(Notification.objects.count(), 1)


class NotificationApiTests(TestCase):

    def setUp(self):
        self.zhai, self.zhai_client = self.create_user_and_client('zhai')
        self.zhou, self.zhou_client = self.create_user_and_client('zhou')
        self.zhai_tweet = self.create_tweet(self.zhai)

    def test_unread_count(self):
        self.zhou_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'content_id': self.zhai_tweet.id,
        })

        url = '/api/notifications/unread-count/'
        response = self.zhai_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['unread_count'], 1)

        comment = self.create_comment(self.zhai, self.zhai_tweet)
        self.zhou_client.post(LIKE_URL, {
            'content_type': 'comment',
            'content_id': comment.id,
        })
        response = self.zhai_client.get(url)
        self.assertEqual(response.data['unread_count'], 2)
        response = self.zhou_client.get(url)
        self.assertEqual(response.data['unread_count'], 0)

    def test_mark_all_as_read(self):
        self.zhou_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'content_id': self.zhai_tweet.id,
        })
        comment = self.create_comment(self.zhai, self.zhai_tweet)
        self.zhou_client.post(LIKE_URL, {
            'content_type': 'comment',
            'content_id': comment.id,
        })

        unread_url = '/api/notifications/unread-count/'
        response = self.zhai_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 2)

        mark_url = '/api/notifications/mark-all-as-read/'
        response = self.zhai_client.get(mark_url)
        self.assertEqual(response.status_code, 405)
        response = self.zhai_client.post(mark_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['marked_count'], 2)
        response = self.zhai_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 0)

    def test_list(self):
        self.zhou_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'content_id': self.zhai_tweet.id,
        })
        comment = self.create_comment(self.zhai, self.zhai_tweet)
        self.zhou_client.post(LIKE_URL, {
            'content_type': 'comment',
            'content_id': comment.id,
        })

        # auth first
        response = self.anonymous_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, 403)
        # would not send to sender himself
        response = self.zhou_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        # 2
        response = self.zhai_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        # mark one get one
        notification = self.zhai.notifications.first()
        notification.unread = False
        notification.save()
        response = self.zhai_client.get(NOTIFICATION_URL)
        self.assertEqual(response.data['count'], 2)
        response = self.zhai_client.get(NOTIFICATION_URL, {'unread': True})
        self.assertEqual(response.data['count'], 1)
        response = self.zhai_client.get(NOTIFICATION_URL, {'unread': False})
        self.assertEqual(response.data['count'], 1)
    
    def test_update(self):
        self.zhou_client.post(LIKE_URL, {
            'content_type': 'tweet',
            'content_id': self.zhai_tweet.id,
        })
        comment = self.create_comment(self.zhai, self.zhai_tweet)
        self.zhou_client.post(LIKE_URL, {
            'content_type': 'comment',
            'content_id': comment.id,
        })
        notification = self.zhai.notifications.first()

        url = '/api/notifications/{}/'.format(notification.id)
        # put
        response = self.zhou_client.post(url, {'unread': False})
        self.assertEqual(response.status_code, 405)
        # can only be modified by the user
        response = self.anonymous_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, 403)
        # query_set = self.request.user.notifications.all()
        response = self.zhou_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, 404)
        # marked as read
        response = self.zhai_client.put(url, {'unread': False})
        self.assertEqual(response.status_code, 200)
        unread_url = '/api/notifications/unread-count/'
        response = self.zhai_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 1)

        # marked as unread
        response = self.zhai_client.put(url, {'unread': True})
        response = self.zhai_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 2)
        #only update unread
        response = self.zhai_client.put(url, {'verb': 'how are u', 'unread': False})
        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertNotEqual(notification.verb, 'how are u')

