from django.contrib import admin

from newsfeeds.models import NewsFeed


# Register your models here.
@admin.register(NewsFeed)
class NewsFeedAdmin(admin.ModelAdmin):
    list_display = ('id', 'tweet', 'user' ,'created_at')
    date_hierarchy = 'created_at'
