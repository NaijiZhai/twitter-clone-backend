from django.apps import AppConfig


class NewsfeedsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'newsfeeds'

    def ready(self):
        import newsfeeds.listeners
