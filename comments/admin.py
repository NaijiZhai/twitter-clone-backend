from django.contrib import admin

from comments.models import Comment


# Register your models here.
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'tweet', 'updated_at', 'created_at', 'content')
    date_hierarchy = 'created_at'
