from django.contrib.auth.models import User
from django.test import TestCase
from tweets.models import Tweet
from datetime import datetime,timezone, timedelta



class TweetTests(TestCase):

    def test_hours_to_now(self):
        z = User.objects.create_user(username='zhai')
        tweet = Tweet.objects.create(user=z, content='first test')
        tweet.created_at = datetime.now(timezone.utc) - timedelta(hours=10)
        tweet.save()
        self.assertAlmostEqual(tweet.hours_to_now, 10, delta = 1e5)