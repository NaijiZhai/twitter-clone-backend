from newsfeeds.models import NewsFeed
from newsfeeds.services import NewsFeedService
from newsfeeds.tasks import fanout_newsfeeds_main_task
from testing.testcases import TestCase


class NewsFeedTaskTests(TestCase):

    def setUp(self):
        super(NewsFeedTaskTests, self).setUp()
        self.zhai = self.create_user('zhai')
        self.zhou = self.create_user('zhou')

    def test_fanout_main_task(self):
        tweet = self.create_tweet(self.zhai, 'tweet 1')
        self.create_friendship(self.zhou, self.zhai)
        msg = fanout_newsfeeds_main_task(tweet.id, tweet.created_at, self.zhai.id)
        self.assertEqual(1 + 1, NewsFeed.objects.count())

        self.assertEqual(msg, '1 newsfeeds going to fanout, 1 batches created.')
        cached_list = NewsFeedService.get_cached_newsfeed(self.zhai.id)
        self.assertEqual(len(cached_list), 1)

        for i in range(2):
            user = self.create_user('user{}'.format(i))
            self.create_friendship(user, self.zhai)
        tweet = self.create_tweet(self.zhai, 'tweet 2')
        msg = fanout_newsfeeds_main_task(tweet.id, tweet.created_at, self.zhai.id)
        self.assertEqual(4 + 2, NewsFeed.objects.count())
        self.assertEqual(msg, '3 newsfeeds going to fanout, 1 batches created.')
        cached_list = NewsFeedService.get_cached_newsfeed(self.zhai.id)
        self.assertEqual(len(cached_list), 2)

        user = self.create_user('another user')
        self.create_friendship(user, self.zhai)
        tweet = self.create_tweet(self.zhai, 'tweet 3')
        msg = fanout_newsfeeds_main_task(tweet.id, tweet.created_at, self.zhai.id)
        self.assertEqual(8 + 3, NewsFeed.objects.count())
        self.assertEqual(msg, '4 newsfeeds going to fanout, 2 batches created.')
        cached_list = NewsFeedService.get_cached_newsfeed(self.zhai.id)
        self.assertEqual(len(cached_list), 3)
        cached_list = NewsFeedService.get_cached_newsfeed(self.zhou.id)
        self.assertEqual(len(cached_list), 3)
