import uuid

from celery import shared_task

from friendships.services import FriendshipServices
from newsfeeds.models import NewsFeed

from tweets.models import Tweet


@shared_task(time_limit=360)
def fanout_newsfeed(tweet_id):
    from newsfeeds.services import NewsFeedService
    tag = str(uuid.uuid4())
    tweet = Tweet.objects.get(id=tweet_id)
    newsfeeds = [NewsFeed(tweet=tweet, user=follower, insert_tag=tag) for follower in
                 FriendshipServices.get_followers(tweet)]
    newsfeeds.append(NewsFeed(tweet=tweet, user=tweet.user, insert_tag=tag))
    NewsFeed.objects.bulk_create(newsfeeds)
    newsfeeds = NewsFeed.objects.filter(insert_tag=tag)
    for newsfeed in newsfeeds:
        NewsFeedService.push_newsfeed_to_cache(newsfeed)


    return f'fan out successfully, total {len(newsfeeds)} newsfeeds'