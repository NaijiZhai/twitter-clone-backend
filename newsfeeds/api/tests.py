from rest_framework.test import APIClient

from cache_utils.cache_constants import NEWSFEED_USER_PATTERN
from cache_utils.redis_client import RedisClient
from cache_utils.redis_helper import RedisHelper
from friendships.models import Friendship
from newsfeeds.models import NewsFeed
from newsfeeds.services import NewsFeedService
from testing.testcases import TestCase
from utils.pagination import CustomEndlessPagination
from cache_utils.cache_constants import REDIS_LIST_LIMIT_LENGTH

NEWSFEEDS_URL = '/api/newsfeeds/'
POST_TWEETS_URL = '/api/tweets/'
FOLLOW_URL = '/api/friendships/'


class NewsFeedApiTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.zhai = self.create_user('zhai', email='<EMAIL>')
        self.zhai_client = APIClient()
        self.zhai_client.force_authenticate(self.zhai)

        self.zhou = self.create_user('zhou', email='<EMAIL>')
        self.zhou_client = APIClient()
        self.zhou_client.force_authenticate(self.zhou)

        # create followings and followers for zhou
        for i in range(2):
            follower = self.create_user('zhou_follower{}'.format(i), email='<EMAIL1>{}'.format(i))
            Friendship.objects.create(from_user=follower, to_user=self.zhou)
        for i in range(3):
            following = self.create_user('zhou_following{}'.format(i), email='<EMAIL>{}'.format(i))
            Friendship.objects.create(from_user=self.zhou, to_user=following)

    def tearDown(self):
        self.clear_cache()

    def test_list(self):

        response = self.anonymous_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, 403)

        response = self.zhai_client.post(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, 405)
        # 
        response = self.zhai_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)

        self.zhai_client.post(POST_TWEETS_URL, {'content': 'Hello World'})
        response = self.zhai_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 1)

        self.zhai_client.post(FOLLOW_URL, data={'from_user_id': self.zhai.id, 'to_user_id': self.zhou.id},
                              format='json')
        response = self.zhou_client.post(POST_TWEETS_URL, {
            'content': 'Hello Twitter',
        })
        posted_tweet_id = response.data['id']
        response = self.zhai_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['tweet']['id'], posted_tweet_id)

    def test_pagination(self):
        page_size = CustomEndlessPagination.page_size
        followed_user = self.create_user('followed')
        newsfeeds = []
        for i in range(page_size * 2):
            tweet = self.create_tweet(followed_user)
            newsfeed = self.create_newsfeed(user=self.zhai, tweet=tweet)
            newsfeeds.append(newsfeed)

        newsfeeds = newsfeeds[::-1]

        # pull the first page
        response = self.zhai_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.data['has_next_page'], True)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['results'][0]['id'], newsfeeds[0].id)
        self.assertEqual(response.data['results'][1]['id'], newsfeeds[1].id)
        self.assertEqual(
            response.data['results'][page_size - 1]['id'],
            newsfeeds[page_size - 1].id,
        )

        # pull the second page
        response = self.zhai_client.get(
            NEWSFEEDS_URL,
            {'created_at__lt': newsfeeds[page_size - 1].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        results = response.data['results']
        self.assertEqual(len(results), page_size)
        self.assertEqual(results[0]['id'], newsfeeds[page_size].id)
        self.assertEqual(results[1]['id'], newsfeeds[page_size + 1].id)
        self.assertEqual(
            results[page_size - 1]['id'],
            newsfeeds[2 * page_size - 1].id,
        )

        # pull latest newsfeeds
        response = self.zhai_client.get(
            NEWSFEEDS_URL,
            {'created_at__gt': newsfeeds[0].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 0)
        print(len(newsfeeds))

        tweet = self.create_tweet(followed_user, content='test_bug')

        new_newsfeed = self.create_newsfeed(user=self.zhai, tweet=tweet)
        response = self.zhai_client.get(
            NEWSFEEDS_URL,
            {'created_at__gt': newsfeeds[0].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], new_newsfeed.id)

    def test_user_cache(self):
        profile = self.zhou.profile
        profile.nickname = '1'
        profile.save()

        self.assertEqual(self.zhai.username, 'zhai')
        self.create_newsfeed(self.zhou, self.create_tweet(self.zhai))
        self.create_newsfeed(self.zhou, self.create_tweet(self.zhou))

        response = self.zhou_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'zhou')
        self.assertEqual(results[0]['tweet']['user']['nickname'], '1')
        self.assertEqual(results[1]['tweet']['user']['username'], 'zhai')

        self.zhai.username = '2'
        self.zhai.save()
        profile.nickname = '3'
        profile.save()

        response = self.zhou_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'zhou')
        self.assertEqual(results[0]['tweet']['user']['nickname'], '3')
        self.assertEqual(results[1]['tweet']['user']['username'], '2')

    def test_tweet_cache(self):
        tweet = self.create_tweet(self.zhai, 'content1')
        self.create_newsfeed(self.zhou, tweet)
        response = self.zhou_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'zhai')
        self.assertEqual(results[0]['tweet']['content'], 'content1')

        # update username
        self.zhai.username = '1'
        self.zhai.save()
        response = self.zhou_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], '1')

        # update content
        tweet.content = 'content2'
        tweet.save()
        response = self.zhou_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['content'], 'content2')
        
    def _paginate_to_get_newsfeeds(self, client):
        # paginate until the end
        response = client.get(NEWSFEEDS_URL)
        results = response.data['results']
        while response.data['has_next_page']:
            created_at__lt = response.data['results'][-1]['created_at']
            response = client.get(NEWSFEEDS_URL, {'created_at__lt': created_at__lt})
            results.extend(response.data['results'])
        return results

    def test_redis_list_limit(self):
        list_limit = REDIS_LIST_LIMIT_LENGTH
        page_size = 20
        users = [self.create_user('user{}'.format(i)) for i in range(5)]
        newsfeeds = []
        for i in range(list_limit + page_size):
            tweet = self.create_tweet(user=users[i % 5], content='feed{}'.format(i))
            feed = self.create_newsfeed(self.zhai, tweet)
            newsfeeds.append(feed)
        newsfeeds = newsfeeds[::-1]

        # only cached list_limit objects
        cached_newsfeeds = NewsFeedService.get_cached_newsfeed(self.zhai.id)
        self.assertEqual(len(cached_newsfeeds), list_limit)
        queryset = NewsFeed.objects.filter(user=self.zhai)
        self.assertEqual(queryset.count(), list_limit + page_size)

        results = self._paginate_to_get_newsfeeds(self.zhai_client)
        self.assertEqual(len(results), list_limit + page_size)
        for i in range(list_limit + page_size):
            self.assertEqual(newsfeeds[i].id, results[i]['id'])

        # a followed user created a new tweet
        self.create_friendship(self.zhai, self.zhou)
        new_tweet = self.create_tweet(self.zhou, 'an new tweet')
        NewsFeedService.fanout_to_followers(new_tweet)

        def _test_newsfeeds_after_new_feed_pushed():
            results = self._paginate_to_get_newsfeeds(self.zhai_client)
            self.assertEqual(len(results), list_limit + page_size + 1)
            self.assertEqual(results[0]['tweet']['id'], new_tweet.id)
            for i in range(list_limit + page_size):
                self.assertEqual(newsfeeds[i].id, results[i + 1]['id'])

        _test_newsfeeds_after_new_feed_pushed()

        # cache expired
        self.clear_cache()
        _test_newsfeeds_after_new_feed_pushed()

