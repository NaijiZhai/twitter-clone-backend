from django.db.models.signals import post_save
from django.dispatch import receiver

from newsfeeds.models import NewsFeed
from newsfeeds.services import NewsFeedService


@receiver(post_save, sender = NewsFeed)
def push_newsfeed_to_cache(sender, instance, created, **kwargs):
    if not created:
        return
    NewsFeedService.push_newsfeed_to_cache(instance)