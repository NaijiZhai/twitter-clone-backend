
from django.test import TestCase
from django.utils import timezone

from comments.models import Comment
# Create your tests here.
from testing.testcases import TestCase
from rest_framework.test import APIClient

from tweets.models import Tweet

COMMENT_URL = '/api/comments/'
TWEET_LIST_API = '/api/tweets/'
TWEET_DETAIL_API = '/api/tweets/{}/'
NEWSFEED_LIST_API = '/api/newsfeeds/'


class CommentApiTests(TestCase):

    def setUp(self):
        self.zhai = self.create_user('zhai')
        self.zhai_client = APIClient()
        self.zhai_client.force_authenticate(self.zhai)
        self.zhou = self.create_user('zhou')
        self.zhou_client = APIClient()
        self.zhou_client.force_authenticate(self.zhou)

        self.tweet = self.create_tweet(self.zhai)

    def test_create(self):
        # log in
        response = self.anonymous_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, 403)

        # args
        response = self.zhai_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, 400)

        # content
        response = self.zhai_client.post(COMMENT_URL, {'tweet_id': self.tweet.id})
        self.assertEqual(response.status_code, 400)

        # tweet_id
        response = self.zhai_client.post(COMMENT_URL, {'content': '1'})
        self.assertEqual(response.status_code, 400)

        # content len <= 140
        response = self.zhai_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1' * 141,
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual('content' in response.data['errors'], True)

        # both tweet_id user_id
        response = self.zhai_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['user']['id'], self.zhai.id)
        self.assertEqual(response.data['tweet_id'], self.tweet.id)
        self.assertEqual(response.data['content'], '1')

    def test_destroy(self):
        comment = self.create_comment(self.zhai, self.tweet)
        url = '{}{}/'.format(COMMENT_URL, comment.id)

        # 匿名不可以删除
        response = self.anonymous_client.delete(url)
        self.assertEqual(response.status_code, 403)

        # 非本人不能删除
        response = self.zhou_client.delete(url)
        self.assertEqual(response.status_code, 403)

        # 本人可以删除
        count = Comment.objects.count()
        response = self.zhai_client.delete(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), count - 1)

    def test_update(self):
        comment = self.create_comment(self.zhai, self.tweet, 'original')
        another_tweet = self.create_tweet(self.zhou)
        url = '{}{}/'.format(COMMENT_URL, comment.id)

        # 使用 put 的情况下
        # 匿名不可以更新
        response = self.anonymous_client.put(url, {'content': 'new'})
        self.assertEqual(response.status_code, 403)
        # 非本人不能更新
        response = self.zhou_client.put(url, {'content': 'new'})
        self.assertEqual(response.status_code, 403)
        comment.refresh_from_db()
        self.assertNotEqual(comment.content, 'new')
        # 不能更新除 content 外的内容，静默处理，只更新内容
        before_updated_at = comment.updated_at
        before_created_at = comment.created_at
        now = timezone.now()
        response = self.zhai_client.put(url, {
            'content': 'new',
            'user_id': self.zhou.id,
            'tweet_id': another_tweet.id,
            'created_at': now,
        })
        self.assertEqual(response.status_code, 200)
        comment.refresh_from_db()
        self.assertEqual(comment.content, 'new')
        self.assertEqual(comment.user, self.zhai)
        self.assertEqual(comment.tweet, self.tweet)
        self.assertEqual(comment.created_at, before_created_at)
        self.assertNotEqual(comment.created_at, now)
        self.assertNotEqual(comment.updated_at, before_updated_at)

    def test_list(self):
        # 必须带 tweet_id
        response = self.anonymous_client.get(COMMENT_URL)
        self.assertEqual(response.status_code, 400)

        # 带了 tweet_id 可以访问
        # 一开始没有评论
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['comments']), 0)

        # 评论按照时间顺序排序
        self.create_comment(self.zhai, self.tweet, '1')
        self.create_comment(self.zhou, self.tweet, '2')
        self.create_comment(self.zhou, self.create_tweet(self.zhou), '3')
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
        })
        self.assertEqual(len(response.data['comments']), 2)
        self.assertEqual(response.data['comments'][0]['content'], '1')
        self.assertEqual(response.data['comments'][1]['content'], '2')

        # 同时提供 user_id 和 tweet_id 只有 tweet_id 会在 filter 中生效
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'user_id': self.zhai.id,
        })
        self.assertEqual(len(response.data['comments']), 2)
        
        
        
    def test_comments_count(self):
        # test tweet detail api
        tweet = self.create_tweet(self.zhai)
        url = TWEET_DETAIL_API.format(tweet.id)
        response = self.zhou_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['comment_count'], 0)

        # test tweet list api
        self.create_comment(self.zhai, tweet)
        response = self.zhou_client.get(TWEET_LIST_API, {'user_id': self.zhai.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['tweets'][0]['comment_count'], 1)

        # test newsfeeds list api
        self.create_comment(self.zhou, tweet)
        self.create_newsfeed(self.zhou, tweet)
        response = self.zhou_client.get(NEWSFEED_LIST_API)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['newsfeeds'][0]['tweet']['comment_count'], 2)