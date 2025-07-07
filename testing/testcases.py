import random
from functools import cached_property

from django.contrib.contenttypes.models import ContentType
from django.core.cache import caches
from django.test import TestCase as DjangoTestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from cache_utils.redis_client import RedisClient
from comments.models import Comment
from friendships.models import Friendship
from likes.models import Like
from newsfeeds.models import NewsFeed
from tweets.models import Tweet


class TestCase(DjangoTestCase):

    @cached_property
    def anonymous_client(self):
        return APIClient()

    def create_user(self, username, email = None, password=None):
        if password is None:
            password = 'generic password'
        if not email:
            email = str(random.randint(0,10000)) + '@a.com'
        return User.objects.create_user(username, email, password)

    def create_tweet(self, user, content=None):
        if content is None:
            content = 'default tweet content'
        return Tweet.objects.create(user=user, content=content)

    def create_comment(self, user, tweet, content=None):
        if content is None:
            content = 'default comment content'
        return Comment.objects.create(user=user, tweet=tweet, content=content)

    def create_like(self, user, target):
        instance, _ = Like.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(target.__class__),
            content_id=target.id,
            user=user,
        )
        return instance

    def create_friendship(self, from_user, to_user):
        return Friendship.objects.create(from_user=from_user, to_user=to_user)


    def create_newsfeed(self, user, tweet):
        return NewsFeed.objects.create(user=user, tweet=tweet)


    def create_user_and_client(self, *args, **kwargs):
        user = self.create_user(*args, **kwargs)
        client = APIClient()
        client.force_authenticate(user)
        return user, client

    def clear_cache(self):
        RedisClient.clear()
        caches['testing'].clear()