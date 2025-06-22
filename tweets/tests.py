from django.contrib.contenttypes.models import ContentType

from likes.models import Like
from testing.testcases import TestCase
from tweets.constants import TweetPhotoStatus
from tweets.models import TweetPhoto


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
