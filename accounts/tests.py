from accounts.models import UserProfile
from testing.testcases import TestCase


class UserProfileTests(TestCase):

    def test_profile_property(self):
        zhai = self.create_user('zhai')
        p = zhai.profile
        self.assertEqual(isinstance(p, UserProfile), True)
        self.assertEqual(UserProfile.objects.count(), 1)

