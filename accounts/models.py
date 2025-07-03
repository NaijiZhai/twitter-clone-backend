from django.contrib.auth.models import User
from django.db import models


# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True)
    avatar = models.FileField(null = True)
    biography = models.TextField(blank=True)
    nickname = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username}\'s profile'

# Add the profile property to User model
def get_user_profile(user):
    from accounts.services import UserServices
    if hasattr(user, '_userprofile'):
        return getattr(user, '_userprofile')
    profile =  UserServices.get_userprofile_by_user_id_through_cache(user.id)
    setattr(user, '_userprofile', profile)
    return profile

User.add_to_class('profile', property(get_user_profile))



