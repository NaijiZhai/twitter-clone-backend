from accounts.models import UserProfile
from testing.testcases import TestCase
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

LOGIN_URL = '/api/accounts/login/'
LOGOUT_URL = '/api/accounts/logout/'
SIGNUP_URL = '/api/accounts/signup/'
LOGIN_STATUS_URL = '/api/accounts/login_status/'
USER_PROFILE_DETAIL_URL = '/api/profiles/{}/'

class AccountApiTests(TestCase):

    def setUp(self):
        # @before
        self.client = APIClient()
        self.user = self.create_user(
            username='admin',
            email='admin@zhai.com',
            password='correct password',
        )


    def test_login(self):
        response = self.client.get(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })
        # should not use get
        self.assertEqual(response.status_code, 405)

        response = self.client.put(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })
        self.assertEqual(response.status_code, 405)

        # wrong password
        response = self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'password': 'wrong password',
        })
        self.assertEqual(response.status_code, 400)

        #wrong username
        response = self.client.post(LOGIN_URL, {
            'username': self.user.username + str('suffix'),
            'password': 'correct password',
        })
        self.assertEqual(response.status_code, 400)

        # has not logged in
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], False)
        # log in
        response = self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data['user'], None)
        self.assertEqual(response.data['user']['email'], 'admin@zhai.com')
        # has not logged in
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

    def test_logout(self):
        # log in
        self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })
        # test logged in
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

        # get is not allowed
        response = self.client.get(LOGOUT_URL)
        self.assertEqual(response.status_code, 405)

        # use post
        response = self.client.post(LOGOUT_URL)
        self.assertEqual(response.status_code, 200)
        # logged out
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], False)

    def test_signup(self):
        data = {
            'username': 'someone',
            'email': 'someone@zhai.com',
            'password': 'any password',
        }
        # get is not allowed
        response = self.client.get(SIGNUP_URL, data)
        self.assertEqual(response.status_code, 405)

        # 测试错误的邮箱
        response = self.client.post(SIGNUP_URL, {
            'username': 'someone',
            'email': 'not a correct email',
            'password': 'any password'
        })
        # print(response.data)
        self.assertEqual(response.status_code, 400)

        # 测试密码太短
        response = self.client.post(SIGNUP_URL, {
            'username': 'someone',
            'email': 'someone@zhai.com',
            'password': '123',
        })
        # print(response.data)
        self.assertEqual(response.status_code, 400)

        # 测试用户名太长
        response = self.client.post(SIGNUP_URL, {
            'username': 'username is tooooooooooooooooo loooooooooooong',
            'email': 'someone@zhai.com',
            'password': 'any password',
        })
        # print(response.data)
        self.assertEqual(response.status_code, 400)

        # 成功注册
        response = self.client.post(SIGNUP_URL, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(UserProfile.objects.count(),2)
        self.assertIsNotNone(UserProfile.objects.filter(user__username='someone').first())
        self.assertEqual(response.data['user']['username'], 'someone')
        # 验证用户已经登入
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)
        
        
class UserProfileAPITests(TestCase):

    def test_update(self):
        zhai, zhai_client = self.create_user_and_client('zhai')
        p = zhai.profile
        p.nickname = 'old nickname'
        p.save()
        url = USER_PROFILE_DETAIL_URL.format(p.id)

        response = self.anonymous_client.put(url,  {'nickname': 'a new nickname'})
        self.assertEqual(response.status_code, 403)

        # test can only be updated by user himself.
        _, zhou_client = self.create_user_and_client('zhou')
        response = zhou_client.put(url, {
            'nickname': 'a new nickname',
        })
        self.assertEqual(response.status_code, 403)
        p.refresh_from_db()
        self.assertEqual(p.nickname, 'old nickname')

        # update nickname
        response = zhai_client.put(url, {
            'nickname': 'a new nickname',
        })
        self.assertEqual(response.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.nickname, 'a new nickname')

        # update avatar
        response = zhai_client.put(url, {
            'avatar': SimpleUploadedFile(
                name='zhai-avatar.jpg',
                content=str.encode('a fake image'),
                content_type='image/jpeg',
            ),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual('zhai-avatar' in response.data['avatar'], True)
        p.refresh_from_db()
        self.assertIsNotNone(p.avatar)
