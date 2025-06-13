from testing.testcases import TestCase


LIKE_BASE_URL = '/api/likes/'


class LikeApiTests(TestCase):

    def setUp(self):
        self.zhai, self.zhai_client = self.create_user_and_client('linghu')
        self.zhou, self.zhou_client = self.create_user_and_client('dongxie')

    def test_tweet_likes(self):
        tweet = self.create_tweet(self.zhai)
        data = {'content_type': 'tweet', 'content_id': tweet.id}

        # anonymous is not allowed
        response = self.anonymous_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, 403)

        # get is not allowed
        response = self.zhai_client.get(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, 405)

        # post success
        response = self.zhai_client.post(LIKE_BASE_URL, data)
        print(response.data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(tweet.like_set.count(), 1)

        # duplicate likes
        self.zhai_client.post(LIKE_BASE_URL, data)
        self.assertEqual(tweet.like_set.count(), 1)
        self.zhou_client.post(LIKE_BASE_URL, data)
        self.assertEqual(tweet.like_set.count(), 2)

    def test_comment_likes(self):
        tweet = self.create_tweet(self.zhai)
        comment = self.create_comment(self.zhou, tweet)
        data = {'content_type': 'comment', 'content_id': comment.id}

        # anonymous is not allowed
        response = self.anonymous_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, 403)

        # get is not allowed
        response = self.zhai_client.get(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, 405)

        # wrong content_type
        response = self.zhai_client.post(LIKE_BASE_URL, {
            'content_type': 'coment',
            'content_id': comment.id,
        })
        self.assertEqual(response.status_code, 400)
        print(response.data)
        self.assertEqual('content_type' in response.data['errors'], True)

        # wrong content_id
        response = self.zhai_client.post(LIKE_BASE_URL, {
            'content_type': 'comment',
            'content_id': -1,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual('content_id'in response.data['errors'], True)

        # post success
        response = self.zhai_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(comment.like_set.count(), 1)

        # duplicate likes
        response = self.zhai_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(comment.like_set.count(), 1)
        self.zhou_client.post(LIKE_BASE_URL, data)
        self.assertEqual(comment.like_set.count(), 2)
