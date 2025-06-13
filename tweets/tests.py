from django.contrib.contenttypes.models import ContentType

from likes.models import Like
from testing.testcases import TestCase


class TweetTests(TestCase):

    def test_like(self):
        user = self.create_user('user1')
        tweet = self.create_tweet(user=user)
        self.create_like(user=user, target=tweet)
        like = Like.objects.filter(content_type=ContentType.objects.get_for_model(tweet.__class__), content_id=tweet.id).first()
        self.assertNotEquals(like, None)
