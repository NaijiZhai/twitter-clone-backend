from testing.testcases import TestCase


class CommentModelTests(TestCase):

    def setUp(self):
        self.zhai = self.create_user('zhai')
        self.tweet = self.create_tweet(self.zhai)
        self.comment = self.create_comment(self.zhai, self.tweet)

    def test_comment(self):
        self.assertNotEqual(self.comment.__str__(), None)

    def test_like_set(self):
        self.create_like(self.zhai, self.comment)
        self.assertEqual(self.comment.like_set.count(), 1)

        self.create_like(self.zhai, self.comment)
        self.assertEqual(self.comment.like_set.count(), 1)

        zhou = self.create_user('zhou')
        self.create_like(zhou, self.comment)
        self.assertEqual(self.comment.like_set.count(), 2)
