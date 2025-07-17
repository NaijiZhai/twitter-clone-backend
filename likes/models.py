from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.auth.models import User

from cache_utils.cache_utils import CacheUtils


# Create your models here.
class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True)
    content_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'content_id')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'content_type', 'content_id'],
                name='unique_user_content_like'
            )
        ]
        indexes = [
            models.Index(
                fields=['content_type', 'content_id', 'created_at'],
                name='idx_ct_id_created_at'
            ),
            models.Index(
                fields=['user', 'content_type', 'content_id', 'created_at'],
                name='idx_user_ct_id_created_at'
            )
        ]

    def __str__(self):
        return f'{self.user} likes {self.target} at {self.created_at}'

    @property
    def cached_user(self):
        return CacheUtils.get_object_in_cache(User, self.user_id)
