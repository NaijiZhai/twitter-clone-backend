# Twitter Clone Project

A Django-based Twitter clone project that implements core social media platform features.

## Features

### Core Functionality
- **User Management** - User registration, login, profile management
- **Tweet System** - Create, view, delete tweets with photo upload support
- **Social Relationships** - Follow/unfollow users functionality
- **Interaction Features** - Like tweets and comments
- **Comment System** - Comment on tweets(TBD: comment on comments)
- **News Feed** - Personalized timeline showing tweets from followed users
- **Notification System** - Real-time user interaction notifications

### Technical Features
- **Cache Optimization** - Redis caching for improved performance
- **Async Processing** - Celery integration for background tasks
- **Database Indexing** - Optimized query performance
- **API Design** - RESTful API architecture
- **File Upload** - Image upload functionality

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

## Tech Stack

- **Framework**: Django 4.2.21
- **Database**: MySQL
- **Cache**: Redis
- **Async Tasks**: Celery
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
# Create database migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start Django development server
python manage.py runserver

# Start Celery worker (new terminal)
celery -A twitter worker -l info

## API Endpoints
### User Related
- `/admin` - Django administration
- `POST /api/accounts/signup/` - User registration
- `POST /api/accounts/login/` - User login
- `POST /api/accounts/logout/` - User logout
- `GET /api/accounts/login_status/` - Get login status
- `GET /api/profiles/` - Get and user profile

### Tweet Related
- `GET /api/tweets/` - Get tweet list
- `POST /api/tweets/` - Create tweet
- `GET /api/tweets/<pk>/?comment_limit` - Get a specific tweet(comment_limit is an optional argument)
- `DELETE /api/tweets/<id>/` - Delete tweet

### Friendship Related
- `GET /api/friendships/` - Get following list
- `POST /api/friendships/` - Follow user
- `DELETE /api/friendships/<id>/` - Unfollow user

### Like Related
- `POST /api/likes/` - Like content
- `DELETE /api/likes/<id>/` - Unlike content

### Comment Related
- `GET /api/comments/` - Get comment list
- `POST /api/comments/` - Post comment

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
