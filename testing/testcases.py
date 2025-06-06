import random
from functools import cached_property

from django.test import TestCase as DjangoTestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from comments.models import Comment
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