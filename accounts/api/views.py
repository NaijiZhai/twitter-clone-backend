from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework import permissions
from rest_framework.response import Response
from django.contrib.auth import (logout as django_logout,
                                 login as django_login,
                                 authenticate as django_authenticate)

from accounts.api.serializers import UserSerializer, LoginSerializer,  SignupSerializer
from rest_framework.decorators import action
from rest_framework.request import Request


class AccountViewSet(viewsets.ViewSet):
    serializer_class = SignupSerializer

    @action(detail = False, methods = ['get'])
    def login_status(self, request):
        # print("user：", request.user)
        # print("logged_in：", request.user.is_authenticated)
        # print("auth：", request.auth)
        return_data = {'has_logged_in': request.user.is_authenticated}
        if request.user.is_authenticated:
            return_data['user'] = UserSerializer(instance = request.user).data
        return_data['ip'] = request.META.get('REMOTE_ADDR')
        return Response(return_data)
    @action(detail = False, methods = ['post'])
    def logout(self, request):
        django_logout(request)
        return Response({'success': True})
    @action(detail = False, methods = ['post'])
    def login(self, request):
        serializer = LoginSerializer(data = request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'please check your data',
                'error': serializer.errors
            },status=status.HTTP_400_BAD_REQUEST
            )
        if not User.objects.filter(username = serializer.validated_data['username']).exists():
            return Response({
                "success": False,
                "message": "Please check input.",
                "errors": {
                    "username": [
                        "User does not exist."
                    ]
                }
            },status = 400)
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        user = django_authenticate(username = username, password = password)
        if not user or  user.is_anonymous:
            return Response({
                'success': False,
                'message': 'error in username or password',
            },status=status.HTTP_400_BAD_REQUEST)
        django_login(request, user)
        return Response({'success': True,
                         'User': UserSerializer(user).data})
    @action(detail = False, methods = ['post'])
    def signup(self, request):

        serializer = SignupSerializer(data = request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'please check your data',
                'errors': serializer.errors
            }, status = 400)
        user = serializer.save()
        django_login(request, user)
        return Response({'success': True,
                         'User': UserSerializer(user).data}, status=201)










