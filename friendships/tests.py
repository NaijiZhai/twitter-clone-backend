from friendships.models import Friendship
from friendships.services import FriendshipServices
from testing.testcases import TestCase


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

        Friendship.objects.filter(from_user=self.zhai, to_user=self.zhou).delete()
        user_id_set = FriendshipServices.get_following_id_set(self.zhai.id)
        self.assertSetEqual(user_id_set, {user1.id, user2.id})
