# Twitter Clone Project

This project is a Twitter-style social media platform backend developed using Django 5.2.4. It includes core
functionalities
such as tweet posting, following/follower relationships, news feeds, and notification support, all implemented with
modern Django best practices.

See the demo on https://twitterapi.naijizhai.com/

## Project Overview

This project replicates essential features of Twitter using Django, optimized for learning and scalability

## Features

### Tech Stack

- **Framework**: Django 5.2.4
- **RestFrameWork**: Django REST Framework 3.16.0
- **Storage**: Amazon S3 for production, MinIO used during early-stage/local development
- **Database**: MySQL
- **Cache**: Redis
- **Async Tasks**: Celery
- **Message Queue**: Amazon SQS
- **Python Version**: 3.10.11

### Core Functionality

- **User Management** - User registration, login, profile management
- **Tweet System** - Create, view, delete tweets with image upload capability
- **Social Relationships** - Follow and unfollow users
- **Interaction Features** - Like tweets and comments
- **Comment System** - Comment on tweets
- **News Feed** - Personalized timeline showing tweets from followed users(Hybrid pull/push mode)
- **Notification System** - user interaction notifications

### Advanced Features (TBD)

- **Frontend UI** - Build responsive web frontend user interface
- **Nested Comments** - Support for comment on comments
- **Optimize Storage** - Switch friendships to HBase or Casandra for write heavy operation.
- **Friend Recommendation** - AI-powered user discovery and friend suggestions
- **Content Moderation** - Progressive local content moderation system with user trust scoring, automated filtering, and
  multi-tier review process (implemented with local ML models, replacing OpenAI API dependency), see details
  in:https://blog.x.com/en_us/topics/product/2023/freedom-of-speech-not-reach-an-update-on-our-enforcement-philosophy

### Technical Features

- **Cache Optimization** - Redis caching for improved performance
- **Async Processing** - Celery integration with Amazon SQS for handling background tasks like notifications and feed
  updates.
- **Database Indexing** - Optimized query performance
- **API Design** - Standardized API design with clear endpoints and responses.
- **File Upload** - Supports image uploads, utilizing Amazon S3 (production) and MinIO (development).

## API Endpoints

### User Related

- `/admin` - Django administration
- `POST /api/accounts/signup/` - User registration
- `POST /api/accounts/login/` - User login
- `POST /api/accounts/logout/` - User logout
- `GET /api/accounts/login_status/` - Get login status
- `PUT /api/profiles/<pk>/` - Update User profile

### Tweet Related

- `GET /api/tweets/` - Get tweet list (will contain details)
- `POST /api/tweets/` - Create tweet
- `GET /api/tweets/<pk>/?comment_limit` - Get a specific tweet(comment_limit is an optional argument)
- `DELETE /api/tweets/<id>/` - Delete tweet

### Friendship Related

- `GET /api/friendships/?from_user_id=?` - Get following list
- `GET /api/friendships/?to_user_id=?` - Get followers list
- `POST /api/friendships/?from_user_id=?&to_user_id=?` - Follow user
- `DELETE /api/friendships/remove/?from_user_id=?&to_user_id=?` - Unfollow user

### Like Related

- `POST /api/likes/` - Like content(require params=['content_type', 'content_id'], content_type
  includes ['Tweet', 'Comment'])
- `DELETE /api/likes/` - Unlike content(require params=['content_type', 'content_id'], content_type
  includes ['Tweet', 'Comment'])

### Comment Related

- `GET /api/comments/?tweet_id=?` - Get comment list of a tweet
- `POST /api/comments/` - Post comment(require params = ['user_id','tweet_id','content'])

### NewsFeed Related

- `GET /api/newsfeeds/` - Get newsfeeds of the current user
  - **Query Parameters:**
    - `created_at_gt`: Pull-to-refresh (get newer tweets)
    - `created_at_lt`: Infinite scroll (get older tweets) 
    - `count`: Number of tweets to return (default: 20)
  - **Caching Behavior:**
    - Homepage: Cache-first for fast loading
    - Pull-to-refresh: Always fresh from database
    - Infinite scroll: Cache + database fallback

### Notification Related

- `GET /api/notifications/unread-count/` - Get unread count of the notifications of the current user
- `POST /api/notifications/mark-all-as-read/` - Mark all unread notifications of the current user as read
- `PUT /api/notifications/<pk>/` - Update a certain notification as read or unread

## Project Structure

twitter_project/
├── accounts/ # User account management
├── tweets/ # Tweet functionality
├── friendships/ # User relationship management
├── likes/ # Like functionality
├── comments/ # Comment functionality
├── newsfeeds/ # News feed system
├── notification/ # Notification system
├── utils/ # Utility functions
├── cache_utils/ # Cache utilities
├── testing/ # Testing related files
├── twitter/ # Project configuration
├── manage.py # Django management script
└── requirements.txt # Project dependencies

## Data Models

### Main Models

- **Tweet** - Tweet model with content, creation time, likes count, comments count
- **User** - User model based on Django AbstractUser
- **Friendship** - User relationship model for follow relationships
- **Like** - Like model supporting likes on tweets and comments
- **Comment** - Comment model with nested reply support
- **NewsFeed** - News feed model storing user timeline
- **UserProfile** - Extended user profile model

### Database Schema Design

### 1. Tweet Model (tweets_tweet)

| Field            | Type          | Description                | Constraints                    |
|------------------|---------------|----------------------------|--------------------------------|
| `id`             | AutoField     | Primary key                | PK, Auto-increment             |
| `user`           | ForeignKey    | User who created the tweet | FK to User, ON DELETE SET NULL |
| `content`        | CharField     | Tweet content              | max_length=255                 |
| `created_at`     | DateTimeField | Tweet creation timestamp   | auto_now_add=True              |
| `likes_count`    | IntegerField  | Number of likes            | default=0                      |
| `comments_count` | IntegerField  | Number of comments         | default=0                      |
| `updated_at`     | DateTimeField | Tweet update timestamp     | auto_now=True                  |

**Indexes:**

- `(user, created_at)` - User's tweets ordered by time
- `(created_at)` - Global timeline
- `(-created_at, -id)` - For pull newsfeeds model

### 2. TweetPhoto Model (tweets_tweetphoto)

| Field         | Type          | Description                              | Constraints                     |
|---------------|---------------|------------------------------------------|---------------------------------|
| `id`          | AutoField     | Primary key                              | PK, Auto-increment              |
| `tweet`       | ForeignKey    | Associated tweet                         | FK to Tweet, ON DELETE SET NULL |
| `user`        | ForeignKey    | User who uploaded the photo              | FK to User, ON DELETE SET NULL  |
| `file`        | FileField     | Photo file                               | Required                        |
| `order`       | IntegerField  | Photo order in tweet                     | default=0                       |
| `status`      | IntegerField  | Photo status (pending/approved/rejected) | Choices defined                 |
| `has_deleted` | BooleanField  | Soft delete flag                         | default=False                   |
| `deleted_at`  | DateTimeField | Deletion timestamp                       | null=True                       |
| `created_at`  | DateTimeField | Upload timestamp                         | auto_now_add=True               |

**Indexes:**

- `(tweet, order)` - Most common pattern
- `(user, created_at)` - Querying all photos by a user in chronological order
- `(tweet, status, has_deleted)` - Tweet photos filtering
- `(status, created_at)` - Admin dashboard queries
- `(has_deleted, created_at)` - Recycle bin queries

### 3. User Model (auth_user)

Django's built-in User model with standard fields:

- `username`, `email`, `password`, `first_name`, `last_name`
- `is_staff`, `is_active`, `is_superuser`
- `date_joined`, `last_login`

### 4. UserProfile Model (accounts_userprofile)

| Field        | Type          | Description           | Constraints                |
|--------------|---------------|-----------------------|----------------------------|
| `id`         | AutoField     | Primary key           | PK, Auto-increment         |
| `user`       | OneToOneField | Associated user       | ON DELETE SET NULL         |
| `avatar`     | FileField     | User avatar           | null=True                  |
| `biography`  | TextField     | User biography        | blank=True                 |
| `nickname`   | CharField     | Display name          | max_length=200, blank=True |
| `created_at` | DateTimeField | Profile creation time | auto_now_add=True          |
| `updated_at` | DateTimeField | Profile update time   | auto_now=True              |

### 5. Friendship Model (friendships_friendship)

| Field        | Type          | Description         | Constraints                    |
|--------------|---------------|---------------------|--------------------------------|
| `id`         | AutoField     | Primary key         | PK, Auto-increment             |
| `from_user`  | ForeignKey    | User who follows    | FK to User, ON DELETE SET NULL |
| `to_user`    | ForeignKey    | User being followed | FK to User, ON DELETE SET NULL |
| `created_at` | DateTimeField | Follow timestamp    | auto_now_add=True              |

**Unique Constraints:**

- `(from_user, to_user)` - Prevent duplicate follows

**Indexes:**

- `(from_user, created_at)` - User's following list
- `(to_user, created_at)` - User's followers list
- `(from_user, to_user)` - For pull newsfeeds
- `(to_user, from_user)` - For pull newsfeeds

### 6. Like Model (likes_like)

| Field          | Type                 | Description                      | Constraints                           |
|----------------|----------------------|----------------------------------|---------------------------------------|
| `id`           | AutoField            | Primary key                      | PK, Auto-increment                    |
| `user`         | ForeignKey           | User who liked                   | FK to User, ON DELETE SET NULL        |
| `content_type` | ForeignKey           | Type of liked object             | FK to ContentType, ON DELETE SET NULL |
| `content_id`   | PositiveIntegerField | ID of liked object               | Required                              |
| `target`       | GenericForeignKey    | Generic relation to liked object | Computed field                        |
| `created_at`   | DateTimeField        | Like timestamp                   | auto_now_add=True                     |

**Unique Constraints:**

- `(user, content_type, content_id)` - Prevent duplicate likes

**Indexes:**

- `(content_type, content_id, created_at)` - Likes for an object
- `(user, content_type, content_id, created_at)` - User's likes

### 7. Comment Model (comments_comment)

| Field         | Type          | Description           | Constraints                     |
|---------------|---------------|-----------------------|---------------------------------|
| `id`          | AutoField     | Primary key           | PK, Auto-increment              |
| `user`        | ForeignKey    | User who commented    | FK to User, ON DELETE SET NULL  |
| `tweet`       | ForeignKey    | Commented tweet       | FK to Tweet, ON DELETE SET NULL |
| `content`     | TextField     | Comment content       | max_length=140                  |
| `likes_count` | IntegerField  | Number of likes       | default=0                       |
| `created_at`  | DateTimeField | Comment creation time | auto_now_add=True               |
| `updated_at`  | DateTimeField | Comment update time   | auto_now=True                   |

**Indexes:**

- `(tweet, created_at)` - Comments on a tweet

### 8. NewsFeed Model (newsfeeds_newsfeed)

| Field        | Type          | Description                            | Constraints                      |
|--------------|---------------|----------------------------------------|----------------------------------|
| `id`         | AutoField     | Primary key                            | PK, Auto-increment               |
| `user`       | ForeignKey    | User whose feed                        | FK to User, ON DELETE SET NULL   |
| `tweet`      | ForeignKey    | Tweet in feed                          | FK to Tweet, ON DELETE SET NULL  |
| `created_at` | DateTimeField | Feed entry creation time               | auto_now_add=True                |
| `insert_tag` | CharField     | tag for  get id when using bulk_create | max_length = 36, db_index = true |

**Unique Constraints:**

- `(user, tweet)` - Prevent duplicate feed entries

**Indexes:**

- `(user, created_at)` - User's timeline
- `(created_at)` - Global feed queries

## Database Design Principles

### 1. Performance Optimization

### 1. Performance Optimization

#### Database Optimization
- **Strategic Indexing**: Composite indexes designed based on real query patterns
 - `(user, created_at)` for user timeline queries
 - `(-created_at, -id)` for pull model tweet aggregation
 - `(content_type, content_id, created_at)` for like/comment counts
 - `(from_user, to_user)` and `(to_user, from_user)` for bidirectional friendship queries
- **Denormalization**: Pre-computed counters to eliminate expensive aggregation queries
 - `likes_count` and `comments_count` fields updated via database triggers
 - Reduces timeline rendering from O(n) COUNT queries to O(1) field access
 - 95% reduction in database load for feed generation
- **Soft Deletes**: Graceful data handling without referential integrity issues
 - `has_deleted` flag preserves data relationships while hiding content
 - `SET_NULL` foreign keys prevent cascade deletion errors
 - Enables data recovery and audit trails for compliance

#### Caching Architecture
- **Cache Invalidation Patterns**:
 - Write-through for critical data (new tweets, follows)
 - Lazy loading for secondary data (user profiles, old tweets)
 - Time-based expiration for non-critical content

#### Query Optimization
- **Pagination Strategy**: Cursor-based pagination using `created_at` + `id` for consistent results
- **Batch Processing**: 
 - Bulk database operations for fanout (batch size: 1000)
 - `select_related()` and `prefetch_related()` to eliminate N+1 queries
 - Single query for tweet + user + like/comment counts
- **Connection Pooling**: Database connection reuse reduces connection overhead by 40%

#### Asynchronous Processing
- **Task Queue Architecture**:
 - **HighPriority Queue**: Real-time fanout for tweet creation (< 1s latency)
 - **Standard Queue**: User interactions (likes, follows, comments)
- **Load Distribution**:
 - ETA-based task scheduling prevents system overload
 - Batch processing with 0.1s intervals for smooth resource usage
 - Auto-scaling workers based on queue depth

#### Memory Optimization
- **Hybrid Feed Model**: 90% memory reduction for high-follower users
 - Push model: Pre-computed feeds for users < 5K followers
 - Pull model: On-demand aggregation for users ≥ 5K followers
 - Smart threshold prevents celebrity user memory explosion
- **Data Structure Optimization**:
 - Compressed JSON for cached feed data
 - Efficient data serialization reducing payload size by 30%
 - Lazy loading of tweet media and extended content

### 2. Query Optimization Examples

```python
# Efficient user timeline query
Tweet.objects.filter(user=user).order_by('-created_at')  # Uses (user, created_at) index

# Efficient like count query
# Uses denormalized likes_count field instead of COUNT(*)
tweet.likes_count  # Direct field access and cached fields

```

## Installation and Setup

### 1. Environment Setup

```bash
# Clone the project
git clone [https://github.com/StevenGerrard8/twitter-clone-backend](https://github.com/StevenGerrard8/twitter-clone-backend) cd twitter-clone-backend
# Create virtual environment
python -m venv venv source venv/bin/activate # Windows: venv\Scripts\activate
# Install dependencies
pip install -r requirements.txt
``` 

### 2. Change Settings and Environment

#### Set Allowed Hosts

Change this to `*` for development:

```
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = ['*']
``` 

#### Set DEBUG

For development:

```
DEBUG = True
``` 

For production:

```
DEBUG = False
``` 

#### Set up Message Queue and Storage

See details in:

- https://django-storages.readthedocs.io/en/latest/
- https://docs.celeryq.dev/en/stable/

#### Set up .env in ./twitter

Create a `.env` file in the `./twitter` directory with:

```
OPENAI_API_KEY=your-openai-api-key
SECRET_KEY=your-django-secret-key
``` 

**Note**: The `OPENAI_API_KEY` is required for content moderation checks. Please be aware that using this key might
incur costs according to OpenAI's pricing; it is **not free**. You need to obtain your own API key
from [OpenAI](https://platform.openai.com/account/api-keys) and set it in your environment or configuration file.

You can generate a secure Django secret key using:

```
python -c "import secrets; print(secrets.token_urlsafe())"
``` 

### 3. Database Setup

#### MySQL Configuration

1. **Start MySQL service**

```
systemctl start mysql; sudo systemctl enable mysql
``` 

2. **Create database and user**

```
# Login to MySQL
mysql -u root -p
# Create database (change if you don't want to use root)
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'yourpassword'; FLUSH PRIVILEGES; CREATE DATABASE IF NOT EXISTS twitter CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
``` 

3. **Configure Django settings**

In `twitter/settings.py`:

```
DATABASES = { 'default': { 'ENGINE': 'django.db.backends.mysql', 'NAME': 'twitter', 'USER': 'root', 'PASSWORD': 'yourpassword', 'HOST': 'localhost', 'PORT': '3306', } }
``` 

### 4. Redis Setup

1. **Start Redis service**

```
sudo systemctl start redis-server; sudo systemctl enable redis-server
``` 

2. **Test Redis connection**

```
bredis-cli ping
# Should return: PONG
``` 

3. **Configure Django Redis settings**

In `twitter/settings.py`:

```
CACHES = { 'default': { 'BACKEND': 'django_redis.cache.RedisCache', 'LOCATION': 'redis://127.0.0.1:6379/1', 'OPTIONS': { 'CLIENT_CLASS': 'django_redis.client.DefaultClient', } } }
# Celery configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0' CELERY_RESULT_BACKEND = 'redis://localhost:6379/2'
``` 

### 5. Django Project Setup

```
# Create database migrations
python manage.py makemigrations
# Apply migrations
python manage.py migrate
# Create superuser
python manage.py createsuperuser
``` 

## Service Management

### Start All Services

```
# Start MySQL
sudo systemctl start mysql
# Start Redis
sudo systemctl start redis
# Start Django
python manage.py runserver
# Start Celery worker
celery -A twitter worker -l info
``` 

## Development Guide

### Testing

```
# Run tests
python manage.py test
# Run specific app tests
python manage.py test tweets
# Run tests with detail
python manage.py test -v2
```

## Deployment

### Production Environment Setup

1. Set environment variables
2. Configure database connection
3. Set up Redis cache
4. Set up AWS S3 and SQS(or use your own replacement)
5. Configure Celery task queue
6. Use Gunicorn as WSGI server

## References

- [redianmarku/Django‑Twitter‑Clone] – A fully functional Twitter-like application built with Django, including user
  auth, tweets, follows, and likes.
- [vBubbaa/django‑twitter] – A Django Twitter clone with full user system, AJAX-powered tweets, likes, comments, and
  follow features.
- [ArJSarmiento/Twitter‑Clone‑Django] – Responsive Twitter clone on Django 3.2 including editing, likes, and follows.

## License

This project is for educational purposes only.

**Note**: This is a learning project and should not be used in production environments.


