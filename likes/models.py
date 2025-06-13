from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.contrib.auth.models import User
# Create your models here.
class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True)
    content_id = models.PositiveIntegerField()
    target = GenericForeignKey('content_type', 'content_id')

    class Meta:
        unique_together = (('user', 'content_type', 'content_id'),)
        index_together = (('content_type', 'content_id', 'created_at'),
                          ('user', 'content_type', 'content_id', 'created_at'))

    def __str__(self):
        return f'{self.user} likes {self.target} at {self.created_at}'
