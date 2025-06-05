import email

from django.contrib.auth.models import User, Group
from rest_framework import serializers

class UserSerializerForTweetResponse(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username')

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'id']

class UserSerializerForFriendship(UserSerializerForTweetResponse):
    pass


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(allow_blank = False, required=True)
    password = serializers.CharField(allow_blank = False, required=True)
    # email = serializers.EmailField(allow_blank = True, required=False)


class SignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'password']
    username = serializers.CharField(allow_blank = False, required=True, max_length=20,min_length=6)
    email = serializers.EmailField()
    password = serializers.CharField(allow_blank = False, required=True,max_length=20,min_length=6,write_only=True)
    def validate(self, data):
        data['email'] = data['email'].lower()
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError("Username already exists")
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("Email already exists")
        return data
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user



