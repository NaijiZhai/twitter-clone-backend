class TweetPhotoStatus:
    PENDING = 0
    UPLOADED = 1
    FAILED = 2
    REJECTED = 3
    DELETED = 4

TWEET_PHOTO_STATUS_CHOICES = (
(TweetPhotoStatus.PENDING, 'Pending'),
(TweetPhotoStatus.UPLOADED, 'Uploaded'),
(TweetPhotoStatus.FAILED, 'Failed'),
(TweetPhotoStatus.REJECTED, 'Rejected'),
(TweetPhotoStatus.DELETED, 'Deleted')
)