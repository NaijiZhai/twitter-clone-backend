# clean_invalid_newsfeeds.py
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'twitter.settings')
django.setup()

from newsfeeds.models import NewsFeed
from django.db.models import Q


def clean_invalid_newsfeeds():
    """清理无效的NewsFeed数据"""
    print("🧹 Cleaning invalid newsfeeds...")

    # 1. 查找user为null的newsfeeds
    null_user_feeds = NewsFeed.objects.filter(user__isnull=True)
    null_user_count = null_user_feeds.count()
    print(f"Found {null_user_count} newsfeeds with null user")

    # 2. 查找tweet为null的newsfeeds
    null_tweet_feeds = NewsFeed.objects.filter(tweet__isnull=True)
    null_tweet_count = null_tweet_feeds.count()
    print(f"Found {null_tweet_count} newsfeeds with null tweet")

    # 3. 查找两者都为null的
    both_null = NewsFeed.objects.filter(
        Q(user__isnull=True) | Q(tweet__isnull=True)
    )
    both_null_count = both_null.count()
    print(f"Found {both_null_count} newsfeeds with null user or tweet")

    # 询问是否删除
    if both_null_count > 0:
        response = input("\nDo you want to delete these invalid newsfeeds? (yes/no): ")
        if response.lower() == 'yes':
            deleted_count = both_null.delete()[0]
            print(f"✅ Deleted {deleted_count} invalid newsfeeds")
        else:
            print("❌ Skipped deletion")

    # 4. 检查数据完整性
    print("\n📊 Data integrity check:")
    total_newsfeeds = NewsFeed.objects.count()
    valid_newsfeeds = NewsFeed.objects.filter(
        user__isnull=False,
        tweet__isnull=False
    ).count()

    print(f"Total newsfeeds: {total_newsfeeds}")
    print(f"Valid newsfeeds: {valid_newsfeeds}")


def check_test_data_integrity():
    """检查测试数据的完整性"""
    print("\n🔍 Checking test data integrity...")

    from django.contrib.auth.models import User
    from tweets.models import Tweet

    # 检查测试用户
    test_users = User.objects.filter(
        username__regex=r'^(celebrity_|influencer_|active_|normal_|lurker_)'
    )
    print(f"Test users: {test_users.count()}")

    # 检查测试推文
    test_tweets = Tweet.objects.filter(
        user__in=test_users
    )
    print(f"Test tweets: {test_tweets.count()}")

    # 检查孤立的newsfeeds（用户或推文被删除）
    orphaned_feeds = NewsFeed.objects.filter(
        Q(user__isnull=True) | Q(tweet__isnull=True)
    ).filter(
        Q(user__username__regex=r'^(celebrity_|influencer_|active_|normal_|lurker_)') |
        Q(tweet__user__username__regex=r'^(celebrity_|influencer_|active_|normal_|lurker_)')
    )

    if orphaned_feeds.exists():
        print(f"⚠️  Found {orphaned_feeds.count()} orphaned test newsfeeds")


if __name__ == '__main__':
    clean_invalid_newsfeeds()
    check_test_data_integrity()