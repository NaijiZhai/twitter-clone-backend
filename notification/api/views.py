from notifications.models import Notification
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notification.api.serializers import NotificationSerializer, NotificationSerializerForUpdate
from utils.decorator import require_all_params


class NotificationViewSet(viewsets.GenericViewSet, viewsets.mixins.ListModelMixin):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated,]
    filterset_fields = ('unread',)

    def get_queryset(self):
        return self.request.user.notifications.all() #this works because recipient is a foreign key

    @action(detail=False, methods = ['get'], url_path='unread-count')
    def unread_count(self, request):
        return Response({'unread_count': self.get_queryset().unread().count()}, status=200)

    @action(detail=False, methods = ['post'], url_path='mark-all-as-read')
    def mark_all_as_read(self, request):
        count = self.get_queryset().mark_all_as_read()
        return Response({'success': True, 'marked_count':count}, status=200)

    @require_all_params(request_attr='data', params=['unread'])
    def update(self, request, *args, **kwargs):
        serializer = NotificationSerializerForUpdate(instance=self.get_object(), data=request.data)
        if not serializer.is_valid():
            return Response({'message': 'error', 'errors': serializer.errors}, status=400)
        notification = serializer.save()
        return Response({'message': 'successfully update','data':NotificationSerializer(notification).data}, status=200)










