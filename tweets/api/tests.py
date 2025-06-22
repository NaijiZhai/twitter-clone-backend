from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from testing.testcases import TestCase
from tweets.models import Tweet, TweetPhoto

TWEET_LIST_API = '/api/tweets/'
TWEET_CREATE_API = '/api/tweets/'
TWEET_RETRIEVE_API = '/api/tweets/{}/'

class TweetApiTests(TestCase):

    def setUp(self):
        self.zhai = self.create_user('zhai', 'zhai@zhai.com')
        self.tweets1 = [
            self.create_tweet(self.zhai)
            for i in range(3)
        ]
        self.zhai_client = APIClient()
        self.zhai_client.force_authenticate(self.zhai)

        self.zhou = self.create_user('zhou', 'zhou@zhai.com')
        self.tweets2 = [
            self.create_tweet(self.zhou)
            for i in range(2)
        ]

    def test_list_api(self):
        # user_id
        response = self.anonymous_client.get(TWEET_LIST_API)
        self.assertEqual(response.status_code, 400)

        # request
        response = self.anonymous_client.get(TWEET_LIST_API, {'user_id': self.zhai.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['tweets']), 3)
        response = self.anonymous_client.get(TWEET_LIST_API, {'user_id': self.zhou.id})
        self.assertEqual(len(response.data['tweets']), 2)
        # test ordering
        self.assertEqual(response.data['tweets'][0]['id'], self.tweets2[1].id)
        self.assertEqual(response.data['tweets'][1]['id'], self.tweets2[0].id)

    def test_create_api(self):
        # log in first
        response = self.anonymous_client.post(TWEET_CREATE_API)
        self.assertEqual(response.status_code, 403)

        # content is needed
        response = self.zhai_client.post(TWEET_CREATE_API)
        self.assertEqual(response.status_code, 400)
        # content too short
        response = self.zhai_client.post(TWEET_CREATE_API, {'content': '1'})
        self.assertEqual(response.status_code, 400)
        # content could not be too long
        response = self.zhai_client.post(TWEET_CREATE_API, {
            'content': '0' * 141
        })
        self.assertEqual(response.status_code, 400)

        # 正常发帖
        tweets_count = Tweet.objects.count()
        response = self.zhai_client.post(TWEET_CREATE_API, {
            'content': 'Hello World, this is my first tweet!'
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['user']['id'], self.zhai.id)
        self.assertEqual(Tweet.objects.count(), tweets_count + 1)

    def test_create_with_photos(self):
        #
        response = self.zhai_client.post(TWEET_CREATE_API, {
            'content': 'a selfie',
            'photos': [],
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(TweetPhoto.objects.count(), 0)


        file = SimpleUploadedFile(
            name='selfie.jpg',
            content=str.encode('a fake image'),
            content_type='image/jpeg',
        )
        response = self.zhai_client.post(TWEET_CREATE_API, {
            'content': 'a selfie',
            'photos': [file],
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(TweetPhoto.objects.count(), 1)

        # test upload more phots
        file1 = SimpleUploadedFile(
            name='selfie1.jpg',
            content=str.encode('selfie 1'),
            content_type='image/jpeg',
        )
        file2 = SimpleUploadedFile(
            name='selfie2.jpg',
            content=str.encode('selfie 2'),
            content_type='image/jpeg',
        )
        response = self.zhai_client.post(TWEET_CREATE_API, {
            'content': 'two selfies',
            'photos': [file1, file2],
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(TweetPhoto.objects.count(), 3)

        # we got all urls
        retrieve_url = TWEET_RETRIEVE_API.format(response.data['id'])
        response = self.zhai_client.get(retrieve_url)
        self.assertEqual(len(response.data['photo_urls']), 2)
        self.assertEqual('selfie1' in response.data['photo_urls'][0], True)
        self.assertEqual('selfie2' in response.data['photo_urls'][1], True)

        # limit = 4
        photos = [
            SimpleUploadedFile(
                name=f'selfie{i}.jpg',
                content=str.encode(f'selfie{i}'),
                content_type='image/jpeg',
            )
            for i in range(5)
        ]
        response = self.zhai_client.post(TWEET_CREATE_API, {
            'content': 'failed due to number of photos exceeded limit',
            'photos': photos,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(TweetPhoto.objects.count(), 3)

    def test_retrieve(self):
        # tweet with id=-1 does not exist
        url = TWEET_RETRIEVE_API.format(-1)
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, 404)

        # will retrieve all comments
        tweet = self.create_tweet(self.zhai)
        url = TWEET_RETRIEVE_API.format(tweet.id)
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['comments']), 0)

        self.create_comment(self.zhou, tweet, 'holly s***')
        self.create_comment(self.zhai, tweet, 'hmm...')
        response = self.anonymous_client.get(url)
        self.assertEqual(len(response.data['comments']), 2)

        # tweet include all details
        profile = self.zhai.profile
        self.assertEqual(response.data['user']['nickname'], profile.nickname)
        self.assertEqual(response.data['user']['avatar_url'], None)