from friendships.models import Friendship
from rest_framework.test import APIClient
from testing.testcases import TestCase
from utils.pagination import CustomPagination

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

        self.zhou = self.create_user('zhou', email='<EMAIL1>')
        self.zhou_client = APIClient()
        self.zhou_client.force_authenticate(self.zhou)

        # create followings and followers for zhou
        for i in range(2):
            follower = self.create_user('zhou_follower{}'.format(i), email='<EMAIL>{}'.format(i))
            Friendship.objects.create(from_user=follower, to_user=self.zhou)
        for i in range(3):
            following = self.create_user('zhou_following{}'.format(i), email='<EMAIL1>{}'.format(i))
            Friendship.objects.create(from_user=self.zhou, to_user=following)

    def test_follow(self):
        url = FOLLOW_URL

        # need logging in
        response = self.anonymous_client.post(url, data={
            'from_user_id': self.zhai.id,
            'to_user_id': self.zhou.id,
        }, format='json')
        self.assertEqual(response.status_code, 403)
        # we need to post
        response = self.zhou_client.get(url)
        self.assertEqual(response.status_code, 400)
        # you cannot follow yourself
        response = self.zhai_client.post(url, data={
            'from_user_id': self.zhai.id,
            'to_user_id': self.zhai.id,
        }, format='json')
        self.assertEqual(response.status_code, 400)
        # follow successfully
        response = self.zhou_client.post(url, data={
            'from_user_id': self.zhou.id,
            'to_user_id': self.zhai.id,
        }, format='json')
        self.assertEqual(response.status_code, 201)
        # 重复 follow 静默成功
        response = self.zhou_client.post(url, data={
            'from_user_id': self.zhou.id,
            'to_user_id': self.zhai.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['duplicate'], True)
        count = Friendship.objects.count()
        response = self.zhai_client.post(url, data={
            'from_user_id': self.zhai.id,
            'to_user_id': self.zhou.id,
        })
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
        response = self.zhou_client.delete(
            url + 'remove/?from_user_id={}'.format(str(self.zhou.id) + '&to_user_id={}'.format(str(self.zhai.id))))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data['delete'], 1)
        self.assertEqual(Friendship.objects.count(), count - 1)
        #
        count = Friendship.objects.count()
        response = self.zhou_client.delete(
            url + 'remove/?from_user_id={}'.format(str(self.zhou.id) + '&to_user_id={}'.format(str(self.zhai.id))))
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
        self.assertEqual(len(response.data['results']['followings']), 3)
        # -created_at
        ts0 = response.data['results']['followings'][0]['created_at']
        ts1 = response.data['results']['followings'][1]['created_at']
        ts2 = response.data['results']['followings'][2]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(ts1 > ts2, True)
        self.assertEqual(
            response.data['results']['followings'][0]['user']['username'],
            'zhou_following2',
        )
        self.assertEqual(
            response.data['results']['followings'][1]['user']['username'],
            'zhou_following1',
        )
        self.assertEqual(
            response.data['results']['followings'][2]['user']['username'],
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
        self.assertEqual(len(response.data['results']['followers']), 2)
        # -created_at
        ts0 = response.data['results']['followers'][0]['created_at']
        ts1 = response.data['results']['followers'][1]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(
            response.data['results']['followers'][0]['user']['username'],
            'zhou_follower1',
        )
        self.assertEqual(
            response.data['results']['followers'][1]['user']['username'],
            'zhou_follower0',
        )

    def test_followers_pagination(self):
        max_page_size = CustomPagination.max_page_size
        page_size = CustomPagination.page_size
        for i in range(page_size * 2):
            follower = self.create_user('zhai_follower{}'.format(i))
            Friendship.objects.create(from_user=follower, to_user=self.zhai)
            if follower.id % 2 == 0:
                Friendship.objects.create(from_user=self.zhou, to_user=follower)

        url = FOLLOWERS_URL+ '?to_user_id={}'.format(self.zhai.id)

        # anonymous hasn't followed any users
        response = self.anonymous_client.get(url+'&page=1')
        for result in response.data['results']['followers']:
            self.assertEqual(result['has_followed'], False)

        # zhou has followed users with even id
        response = self.zhou_client.get(url+'&page=1')
        for result in response.data['results']['followers']:
            has_followed = (result['user']['id'] % 2 == 0)
            self.assertEqual(result['has_followed'], has_followed)

    def test_followings_pagination(self):
        max_page_size = CustomPagination.max_page_size
        page_size = CustomPagination.page_size
        for i in range(page_size * 2):
            following = self.create_user('zhai_following{}'.format(i))
            Friendship.objects.create(from_user=self.zhai, to_user=following)
            if following.id % 2 == 0:
                Friendship.objects.create(from_user=self.zhou, to_user=following)

        url = FOLLOWINGS_URL + '?from_user_id={}'.format(self.zhai.id)
        self._test_friendship_pagination(url, page_size, max_page_size)

        # anonymous hasn't followed any users
        response = self.anonymous_client.get(url+'&page=1')
        for result in response.data['results']['followings']:
            self.assertEqual(result['has_followed'], False)

        # zhou has followed users with even id
        response = self.zhou_client.get(url+'&page=1')
        for result in response.data['results']['followings']:
            has_followed = (result['user']['id'] % 2 == 0)
            self.assertEqual(result['has_followed'], has_followed)

        # zhai has followed all his following users
        response = self.zhai_client.get(url+'&page=1')
        for result in response.data['results']['followings']:
            self.assertEqual(result['has_followed'], True)

    def _test_friendship_pagination(self, url, page_size, max_page_size):
        response = self.anonymous_client.get(url+'&page=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']['followings']), page_size)
        self.assertEqual(response.data['total_pages'], 2)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['page_number'], 1)
        self.assertEqual(response.data['has_next_page'], True)

        response = self.anonymous_client.get(url+'&page=2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']['followings']), page_size)
        self.assertEqual(response.data['total_pages'], 2)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['page_number'], 2)
        self.assertEqual(response.data['has_next_page'], False)

        response = self.anonymous_client.get(url+'&page=3')
        self.assertEqual(response.status_code, 404)

        # test user can not customize page_size exceeds max_page_size
        response = self.anonymous_client.get(url+'&page=1&size={}'.format(max_page_size + 1))
        self.assertEqual(len(response.data['results']['followings']), max_page_size)
        self.assertEqual(response.data['total_pages'], 2)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['page_number'], 1)
        self.assertEqual(response.data['has_next_page'], True)

        # test user can customize page size by param size
        response = self.anonymous_client.get(url+'&page=1&size=2')
        self.assertEqual(len(response.data['results']['followings']), 2)
        self.assertEqual(response.data['total_pages'], page_size)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['page_number'], 1)
        self.assertEqual(response.data['has_next_page'], True)
