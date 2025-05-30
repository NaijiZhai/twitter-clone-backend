from friendships.services import FriendshipServices
from tweets.models import Tweet
from friendships.models import Friendship
from django.contrib.auth.models import User
from newsfeeds.models import NewsFeed


class NewsFeedService(object):
    @classmethod
    def fanout_to_followers(tweet: Tweet):
        followers = FriendshipServices.get_followers(tweet=tweet)
        newsfeeds = [NewsFeed(user = follower, tweet = tweet) for follower in followers]
        newsfeeds.append(NewsFeed(user = tweet.user, tweet = tweet))
        NewsFeed.objects.bulk_create(newsfeeds)
