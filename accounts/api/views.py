from django.contrib.auth import (logout as django_logout,
                                 login as django_login,
                                 authenticate as django_authenticate)
from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.mixins import UpdateModelMixin
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from accounts.api.serializers import UserSerializer, LoginSerializer, SignupSerializer, UserProfileSerializerForUpdate, \
    UserSerializerWithProfile
from accounts.models import UserProfile
from utils.permissions import IsOwner, IsSuperUser


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializerWithProfile
    permission_classes = [IsSuperUser,]


class AccountViewSet(viewsets.ViewSet):
    serializer_class = LoginSerializer

    @action(detail=False, methods=['get'])
    def login_status(self, request):
        return_data = {'has_logged_in': request.user.is_authenticated}
        if request.user.is_authenticated:
            return_data['user'] = UserSerializer(instance=request.user).data
        return_data['ip'] = request.META.get('REMOTE_ADDR')
        return Response(return_data)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        django_logout(request)
        return Response({'success': True})

    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'please check your data',
                'error': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST
            )
        # if not User.objects.filter(username = serializer.validated_data['username']).exists():
        #     return Response({
        #         "success": False,
        #         "message": "Please check input.",
        #         "errors": {
        #             "username": [
        #                 "User does not exist."
        #             ]
        #         }
        #     }, status = 400)
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        user = django_authenticate(username=username, password=password)
        if not user or user.is_anonymous:
            return Response({
                'success': False,
                'message': 'error in username or password',
            }, status=status.HTTP_400_BAD_REQUEST)
        django_login(request, user)
        return Response({'success': True,
                         'user': UserSerializer(user).data})

    @action(detail=False, methods=['post'], serializer_class=SignupSerializer)
    def signup(self, request):

        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'please check your data',
                'errors': serializer.errors
            }, status=400)
        user = serializer.save()

        django_login(request, user)
        return Response({'success': True,
                         'user': UserSerializer(user).data}, status=201)


class UserProfileViewSet(viewsets.GenericViewSet, UpdateModelMixin, ):
    serializer_class = UserProfileSerializerForUpdate
    queryset = UserProfile.objects.all()
    permission_classes = [IsAuthenticated, IsOwner,]
