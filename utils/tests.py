from testing.testcases import TestCase
from cache_utils.redis_client import RedisClient



class UtilsTests(TestCase):

    def setUp(self):
        RedisClient.clear()

    def test_redis_client(self):
        conn = RedisClient.get_connection()
        conn.lpush('redis_key', 'zhai')
        conn.lpush('redis_key', 1998)
        cached_list = conn.lrange('redis_key', 0, -1)
        self.assertEqual(cached_list, [b'1998', b'zhai'])

        RedisClient.clear()
        cached_list = conn.lrange('redis_key', 0, -1)
        self.assertEqual(cached_list, [])
