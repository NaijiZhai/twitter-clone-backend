from friendships.services import FriendshipServices
from tweets.models import Tweet
from friendships.models import Friendship
from django.contrib.auth.models import User
from newsfeeds.models import NewsFeed


class NewsFeedService(object):
    @classmethod
    def fanout_to_followers(cls, tweet: Tweet):
        followers = FriendshipServices.get_followers(tweet = tweet)
        newsfeeds = [NewsFeed(user = follower, tweet = tweet) for follower in followers]
        newsfeeds.append(NewsFeed(user = tweet.user, tweet = tweet))
        NewsFeed.objects.bulk_create(newsfeeds)

    @classmethod
    def inject_newsfeed(cls, from_user : User, to_user : User):
        tweets = Tweet.objects.filter(user_id = from_user).order_by('-created_at')[:3]
        newsfeeds = [NewsFeed(user_id = to_user, tweet= tweet) for tweet in tweets]
        NewsFeed.objects.bulk_create(newsfeeds)


    @classmethod
    def remove_newsfeed(cls, from_user : User, to_user : User):
        NewsFeed.objects.filter(user_id = to_user, tweet__user = from_user).delete()
