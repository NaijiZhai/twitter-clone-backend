from notifications.models import Notification
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import ModelSerializer


class NotificationSerializer(ModelSerializer):
    actor_content_type = SerializerMethodField()
    target_content_type = SerializerMethodField()
    action_object_content_type = SerializerMethodField()


    class Meta:
        model = Notification
        fields = (
            'id',
            'actor_content_type',
            'actor_object_id',
            'verb',
            'action_object_content_type',
            'action_object_object_id',
            'target_content_type',
            'target_object_id',
            'timestamp',
            'unread',
        )

    def get_actor_content_type(self, obj):
        if not obj.actor_content_type:
            return None
        return obj.actor_content_type.model

    def get_target_content_type(self, obj):
        if not obj.target_content_type:
            return None
        return obj.target_content_type.model

    def get_action_object_content_type(self, obj):
        if not obj.action_object_content_type:
            return None
        return obj.action_object_content_type.model


class NotificationSerializerForUpdate(ModelSerializer):

    class Meta:
        model = Notification
        fields = (
            'id',
            'unread',
        )

    def update(self, instance, validated_data):
        instance.unread = validated_data['unread']
        instance.save()
        return instance