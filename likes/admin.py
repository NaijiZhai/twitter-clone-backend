from django.contrib import admin

from likes.models import Like


# Register your models here.
@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = (
        'user','created_at','content_type','content_id','get_target'
    )

    def get_target(self, obj):
        return obj.target

    list_filter = ('user',)
    date_hierarchy = 'created_at'