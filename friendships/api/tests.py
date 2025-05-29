from friendships.models import Friendship
from rest_framework.test import APIClient
from testing.testcases import TestCase


FOLLOW_URL = '/api/friendships/'
UNFOLLOW_URL = '/api/friendships/'
FOLLOWERS_URL = '/api/friendships/'
FOLLOWINGS_URL = '/api/friendships/'


class FriendshipApiTests(TestCase):

    def setUp(self):
        self.anonymous_client = APIClient()

        self.zhai = self.create_user('zhai', email='<EMAIL>')
        self.zhai_client = APIClient()
        self.zhai_client.force_authenticate(self.zhai)

        self.zhou = self.create_user('zhou',email='<EMAIL1>')
        self.zhou_client = APIClient()
        self.zhou_client.force_authenticate(self.zhou)

        # create followings and followers for zhou
        for i in range(2):
            follower = self.create_user('zhou_follower{}'.format(i),email='<EMAIL>{}'.format(i))
            Friendship.objects.create(from_user=follower, to_user=self.zhou)
        for i in range(3):
            following = self.create_user('zhou_following{}'.format(i),email='<EMAIL1>{}'.format(i))
            Friendship.objects.create(from_user=self.zhou, to_user=following)

    def test_follow(self):
        url = FOLLOW_URL

        # need logging in
        response = self.anonymous_client.post(url,data={
            'from_user_id': self.zhai.id,
            'to_user_id': self.zhou.id,
        }, content_type='application/json')
        self.assertEqual(response.status_code, 403)
        # we need to post
        response = self.zhou_client.get(url)
        self.assertEqual(response.status_code, 400)
        # you cannot follow yourself
        response = self.zhai_client.post(url,data={
            'from_user_id': self.zhai.id,
            'to_user_id': self.zhai.id,
        },content_type='application/json')
        self.assertEqual(response.status_code, 400)
        # follow successfully
        response = self.zhou_client.post(url, data= {
            'from_user_id': self.zhou.id,
            'to_user_id': self.zhai.id,
        }, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        # 重复 follow 静默成功
        response = self.zhou_client.post(url, data= {
            'from_user_id': self.zhou.id,
            'to_user_id': self.zhai.id,
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['duplicate'], True)
        count = Friendship.objects.count()
        response = self.zhai_client.post(url, data= {
            'from_user_id': self.zhai.id,
            'to_user_id': self.zhou.id,
        }, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Friendship.objects.count(), count + 1)

    def test_unfollow(self):
        url = UNFOLLOW_URL


        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 403)

        response = self.zhou_client.get(url)
        self.assertEqual(response.status_code, 400)

        response = self.zhai_client.post(url)
        self.assertEqual(response.status_code, 400)

        Friendship.objects.create(from_user=self.zhou, to_user=self.zhai)
        count = Friendship.objects.count()
        response = self.zhou_client.delete(url + '{}/'.format(str(self.zhou.id) + '_' + str(self.zhai.id)))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data['delete'], 1)
        self.assertEqual(Friendship.objects.count(), count - 1)
        #
        count = Friendship.objects.count()
        response = self.zhou_client.delete(url + '{}/'.format(str(self.zhou.id) + '_' + str(self.zhai.id)))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Friendship.objects.count(), count)

    def test_followings(self):
        url = FOLLOWINGS_URL
        # post is not allowed
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 403)
        # get is ok
        response = self.anonymous_client.get(url, data={'from_user_id': self.zhou.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['followings']), 3)
        # -created_at
        ts0 = response.data['followings'][0]['created_at']
        ts1 = response.data['followings'][1]['created_at']
        ts2 = response.data['followings'][2]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(ts1 > ts2, True)
        self.assertEqual(
            response.data['followings'][0]['user']['username'],
            'zhou_following2',
        )
        self.assertEqual(
            response.data['followings'][1]['user']['username'],
            'zhou_following1',
        )
        self.assertEqual(
            response.data['followings'][2]['user']['username'],
            'zhou_following0',
        )

    def test_followers(self):
        url = FOLLOWERS_URL + '?to_user_id={}'.format(self.zhou.id)
        # post is not allowed
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, 403)
        # get is ok
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['followers']), 2)
        # -created_at
        ts0 = response.data['followers'][0]['created_at']
        ts1 = response.data['followers'][1]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(
            response.data['followers'][0]['user']['username'],
            'zhou_follower1',
        )
        self.assertEqual(
            response.data['followers'][1]['user']['username'],
            'zhou_follower0',
        )
