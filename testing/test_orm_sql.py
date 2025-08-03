import os
import sys

import django



#SELECT to_user_id, COUNT(*) AS follower_count FROM friendships_friendship GROUP BY to_user_id ORDER BY follower_count DESC LIMIT 20;

following_ids = [
    112948, 112951, 112954, 112955, 112947, 112953, 112949, 112950, 112952, 112956,
    113346, 113189, 113062, 113224, 113010, 113351, 112998, 113231, 113101, 113261,
]
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'twitter.settings')
django.setup()

def test_orm(following_ids):
    from friendships.models import Friendship
    from django.db.models import Count
    import time

    start = time.time()
    qs = Friendship.objects.filter(to_user_id__in=following_ids).values('to_user_id').annotate(follower_count=Count('from_user'))
    after_orm = time.time()
    data = list(qs)
    after_fetch = time.time()
    result = {row['to_user_id']: row['follower_count'] for row in data}
    after_dict = time.time()

    print(f"ORM build: {after_orm - start:.4f}s")
    print(f"Fetch result: {after_fetch - after_orm:.4f}s")
    print(f"Dict build: {after_dict - after_fetch:.4f}s")
    return result

def test_raw_sql(following_ids):
    from django.db import connection
    import time

    start = time.time()
    placeholders = ','.join(['%s'] * len(following_ids))
    sql = f"""
        SELECT to_user_id, COUNT(*) as follower_count
        FROM friendships_friendship
        WHERE to_user_id IN ({placeholders})
        GROUP BY to_user_id
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, following_ids)
        rows = cursor.fetchall()
        result = {user_id: count for user_id, count in rows}
    print(f"Raw SQL time: {time.time() - start:.4f}s")
    return result


if __name__ == '__main__':
    result_orm = test_orm(following_ids)
    result_raw_sql = test_raw_sql(following_ids)
    assert result_orm == result_raw_sql