import time

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.core.cache import cache
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient

from newsfeeds.services import NewsFeedService
from newsfeeds.models import NewsFeed
from tweets.models import Tweet
from friendships.models import Friendship
from friendships.services import FriendshipServices
from cache_utils.cache_constants import NEWSFEED_USER_PATTERN


class NewsFeedServiceTestCase(TestCase):
    import time

    from django.test import TestCase, TransactionTestCase
    from django.contrib.auth.models import User
    from django.core.cache import cache
    from unittest.mock import patch, MagicMock
    from rest_framework.test import APIClient

    from newsfeeds.services import NewsFeedService
    from newsfeeds.models import NewsFeed
    from tweets.models import Tweet
    from friendships.models import Friendship
    from friendships.services import FriendshipServices
    from cache_utils.cache_constants import NEWSFEED_USER_PATTERN

