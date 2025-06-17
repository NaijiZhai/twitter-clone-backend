from testing.testcases import TestCase
from notification.services import NotificationService
from notifications.models import Notification


class NotificationServiceTests(TestCase):

    def setUp(self):
        self.zhai = self.create_user('zhai')
        self.zhou = self.create_user('zhou')
        self.zhai_tweet = self.create_tweet(self.zhai)

    def test_send_comment_notification(self):
        # do not dispatch notification if tweet user == comment user
        comment = self.create_comment(self.zhai, self.zhai_tweet)
        NotificationService.send_comment_notification(comment)
        self.assertEqual(Notification.objects.count(), 0)

        # dispatch notification if tweet user != comment user
        comment = self.create_comment(self.zhou, self.zhai_tweet)
        NotificationService.send_comment_notification(comment)
        self.assertEqual(Notification.objects.count(), 1)

    def test_send_like_notification(self):
        # do not dispatch notification if tweet user == like user
        like = self.create_like(self.zhai, self.zhai_tweet)
        NotificationService.send_like_notification(like)
        self.assertEqual(Notification.objects.count(), 0)

        # dispatch notification if tweet user != comment user
        like = self.create_comment(self.zhou, self.zhai_tweet)
        NotificationService.send_comment_notification(like)
        self.assertEqual(Notification.objects.count(), 1)



