from friendships.models import Friendship
from friendships.services import FriendshipServices, cache
from testing.testcases import TestCase
from twitter.cache_constants import FOLLOWING_PATTERN


class FriendshipServiceTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.zhai = self.create_user('zhai')
        self.zhou = self.create_user('zhou')

    def test_get_followings(self):
        user1 = self.create_user('user1')
        user2 = self.create_user('user2')
        for to_user in [user1, user2, self.zhou]:
            Friendship.objects.create(from_user=self.zhai, to_user=to_user)

        user_id_set = FriendshipServices.get_following_id_set(self.zhai.id)
        self.assertSetEqual(user_id_set, {user1.id, user2.id, self.zhou.id})
        print(cache.get(FOLLOWING_PATTERN.format(user_id=self.zhai.id)))

        Friendship.objects.filter(from_user=self.zhai, to_user=self.zhou).delete()
        print(cache.get(FOLLOWING_PATTERN.format(user_id=self.zhai.id)))
        user_id_set = FriendshipServices.get_following_id_set(self.zhai.id)
        print(cache.get(FOLLOWING_PATTERN.format(user_id=self.zhai.id)))
        self.assertSetEqual(user_id_set, {user1.id, user2.id})
