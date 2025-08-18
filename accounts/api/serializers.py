import email

from django.contrib.auth.models import User, Group
from rest_framework import serializers

from accounts.models import UserProfile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username','email','id']

class UserSerializerWithProfile(UserSerializer):
    bio = serializers.CharField(source = 'profile.biography')
    nickname = serializers.CharField(source = 'profile.nickname')
    avatar_url = serializers.SerializerMethodField()

    def get_avatar_url(self, obj):
        return obj.profile.avatar.url if obj.profile.avatar else None

    class Meta:
        model = User
        fields = 'id','username','nickname','avatar_url','bio'


class UserSerializerForFriendship(UserSerializerWithProfile):
    pass

class UserSerializerForLike(UserSerializerWithProfile):
    pass

class UserSerializerForComment(UserSerializerWithProfile):
    pass

class UserSerializerForTweetResponse(UserSerializerWithProfile):
    pass

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(allow_blank = False, required=True)
    password = serializers.CharField(allow_blank = False, required=True,style={'input_type': 'password'})
    # email = serializers.EmailField(allow_blank = True, required=False)
    def validate(self, data):
        user = User.objects.filter(username=data['username']).first()
        if user is None:
            raise serializers.ValidationError("Username or password is incorrect")
        if not user.check_password(data['password']):
            raise serializers.ValidationError("Username or password is incorrect")
        return data


class SignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
    username = serializers.CharField(allow_blank = False, required=True, max_length=20,min_length=6)
    email = serializers.EmailField()
    password = serializers.CharField(allow_blank = False,style={'input_type': 'password'}, required=True,max_length=20,min_length=6,write_only=True)
    def validate(self, data):
        data['email'] = data['email'].lower()
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError("Username already exists")
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("Email already exists")
        return data
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        user.profile
        return user


class UserProfileSerializerForUpdate(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['biography', 'nickname', 'avatar']
