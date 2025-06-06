from django.template.context_processors import request
from rest_framework.permissions import BasePermission

class IsOwner(BasePermission):

    message = 'you do not have access to this object'

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user
