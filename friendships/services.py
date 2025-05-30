from django.contrib.auth.models import User

from friendships.models import Friendship
from tweets.models import Tweet


class FriendshipServices(object):
    @classmethod
    def get_followers(self, tweet : Tweet):
        friendships  = Friendship.objects.filter(to_user=tweet.user).prefetch_related('from_user')
        return [friendship.from_user for friendship in friendships]