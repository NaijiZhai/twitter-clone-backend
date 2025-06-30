#use signal
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from accounts.services import UserServices
from accounts.models import UserProfile
from utils.cache_utils import CacheUtils

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def invalidate_user_cache(sender, instance, **kwargs):
    CacheUtils.invalidate_cache(model = sender, id = instance.id)

@receiver(post_save, sender=UserProfile)
def invalidate_userprofile_cache(sender, instance, **kwargs):
    UserServices.invalidate_userprofile_cache(instance.user_id)

@receiver(pre_delete, sender=User)
def invalidate_user_cache_pre_delete(sender, instance, **kwargs):
    CacheUtils.invalidate_cache(model = sender, id = instance.id)

@receiver(pre_delete, sender=UserProfile)
def invalidate_userprofile_cache_pre_delete(sender, instance, **kwargs):
    UserServices.invalidate_userprofile_cache(instance.user_id)


