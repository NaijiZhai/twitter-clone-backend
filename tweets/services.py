import boto3

from tweets.models import TweetPhoto, Tweet


class TweetService(object):

    @classmethod
    def create_photos(cls, tweet : Tweet, photos):
        photo_files = []
        for idx, photo in enumerate(photos):
            photo_files.append(TweetPhoto(tweet = tweet, user = tweet.user, file = photo, order=idx))

        TweetPhoto.objects.bulk_create(photo_files)