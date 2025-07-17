# Twitter Clone Project

A Django-based Twitter clone project that implements core social media platform features,

## References

- [redianmarku/Django‑Twitter‑Clone] – A fully functional Twitter-like application built with Django, including user
  auth, tweets, follows, and likes.
- [vBubbaa/django‑twitter] – A Django Twitter clone with full user system, AJAX-powered tweets, likes, comments, and
  follow features.
- [ArJSarmiento/Twitter‑Clone‑Django] – Responsive Twitter clone on Django 3.2 including editing, likes, and follows.

## Project Overview

This project replicates essential features of Twitter using Django, optimized for learning and scalability

## Features

### Core Functionality

- **User Management** - User registration, login, profile management
- **Tweet System** - Create, view, delete tweets with image upload capability
- **Social Relationships** - Follow and unfollow users
- **Interaction Features** - Like tweets and comments
- **Comment System** - Comment on tweets
- **News Feed** - Personalized timeline showing tweets from followed users
- **Notification System** - Real-time user interaction notifications

### Advanced Features (TBD)

- **Nested Comments** - Support for comment on comments
- **Optimize Storage** - Switch friendships to HBase or Casandra for write heavy operation.
- **Friend Recommendation** - AI-powered user discovery and friend suggestions
- **Content Moderation** - Progressive local content moderation system with user trust scoring, automated filtering, and
  multi-tier review process (implemented with local ML models, replacing OpenAI API dependency)

### Technical Features

- **Cache Optimization** - Redis caching for improved performance
- **Async Processing** - Celery integration with Amazon SQS for handling background tasks like notifications and feed
  updates.
- **Database Indexing** - Optimized query performance
- **API Design** - Standardized API design with clear endpoints and responses.
- **File Upload** - Supports image uploads, utilizing Amazon S3 (production) and MinIO (development).

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

- **Strategic Indexing**: Indexes are created based on common query patterns
- **Denormalization**: `likes_count` and `comments_count` fields avoid expensive COUNT queries
- **Soft Deletes**: `has_deleted` flag and `SET_NULL`

### 2. Query Optimization Examples

```python
# Efficient user timeline query
Tweet.objects.filter(user=user).order_by('-created_at')  # Uses (user, created_at) index

# Efficient like count query
# Uses denormalized likes_count field instead of COUNT(*)
tweet.likes_count  # Direct field access and cached fields

```

## Tech Stack

- **Framework**: Django 4.2.21
- **RestFrameWork**: Django REST Framework 3.16.0
- **Storage**: Amazon S3 for production, MinIO used during early-stage/local development
- **Database**: MySQL (transactional), Apache HBase (for newsfeeds/friendships)
- **Cache**: Redis
- **Async Tasks**: Celery
- **Message Queue**: Amazon SQS
- **Python Version**: 3.10.11

## Installation and Setup

### 1. Environment Setup

```bash
# Clone the project
git clone <https://github.com/StevenGerrard8/twitter_project--1>
cd twitter_project--1

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

```

### 2. Database Setup

#### MySQL Configuration

1. **Start MySQL service**

#### macOS

brew services start mysql

#### Ubuntu/Debian

sudo systemctl start mysql sudo systemctl enable mysql

2. **Create database and user**

#### Login to MySQL

mysql -u root -p

#### Create database

CREATE DATABASE twitter_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

#### Create user and grant privileges

CREATE USER 'twitter_user'@'localhost' IDENTIFIED BY 'your_secure_password'; GRANT ALL PRIVILEGES ON twitter_db.* TO '
twitter_user'@'localhost'; FLUSH PRIVILEGES; EXIT;

3. **Configure Django settings**

#### In twitter/settings.py

DATABASES = { 'default': { 'ENGINE': 'django.db.backends.mysql', 'NAME': 'twitter_db', 'USER': 'twitter_user', '
PASSWORD': 'your_secure_password', 'HOST': 'localhost', 'PORT': '3306', 'OPTIONS': { 'charset': 'utf8mb4', } } }

### 3. Redis Setup

1. **Start Redis service**

#### macOS

brew services start redis

#### Ubuntu/Debian

sudo systemctl start redis-server sudo systemctl enable redis-server

2. **Test Redis connection**
   bash redis-cli ping

#### Should return: PONG

3. **Configure Django Redis settings**

#### In twitter/settings.py

CACHES = { 'default': { 'BACKEND': 'django_redis.cache.RedisCache', 'LOCATION': 'redis://127.0.0.1:6379/1', '
OPTIONS': { 'CLIENT_CLASS': 'django_redis.client.DefaultClient', } } }

#### Celery configuration

CELERY_BROKER_URL = 'redis://localhost:6379/0' CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

### 4. Django Project Setup

#### Create database migrations

python manage.py makemigrations
####Apply migrations
python manage.py migrate
####Create superuser
python manage.py createsuperuser

## Service Management

### Start All Services

#### Start MySQL

sudo systemctl start mysql

#### Start Redis

sudo systemctl start redis

#### Start Django

python manage.py runserver

#### Start Celery worker

celery -A twitter worker -l info

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

### Notification Related

- `GET /api/notifications/unread-count/` - Get unread count of the notifications of the current user
- `POST /api/notifications/mark-all-as-read/` - Mark all unread notifications of the current user as read
- `PUT /api/notifications/<pk>/` - Update a certain notification as read or unread

## Development Guide

### Testing

``` bash
## Run tests
python manage.py test

# Run specific app tests
python manage.py test tweets

# Run  tests with detail
python manage.py test -v2
```

### Code Standards

- Follow PEP 8 coding style
- Use Django best practices
- Write unit tests and integration tests

### Performance Optimization

- Use select_related and prefetch_related for database query optimization
- Implement caching strategies to reduce database load
- Use database indexes for improved query performance

## Deployment

### Production Environment Setup

1. Set environment variables
2. Configure database connection
3. Set up Redis cache
4. Configure Celery task queue
5. Use Gunicorn as WSGI server
6. Configure Nginx as reverse proxy

## License

This project is for educational purposes only.

**Note**: This is a learning project and should not be used in production environments.


