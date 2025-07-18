# content_moderation.py - Optimized version
from django.conf import settings
from openai import OpenAI
from rest_framework import serializers
import logging

logger = logging.getLogger(__name__)


class ContentModerationService:
    """Content moderation service with adjustable thresholds"""

    # Default thresholds for each category (0.0 to 1.0)
    DEFAULT_THRESHOLDS = {
        'hate': 0.7,
        'hate/threatening': 0.7,
        'harassment': 0.7,
        'harassment/threatening': 0.7,
        'self-harm': 0.7,
        'self-harm/intent': 0.7,
        'self-harm/instructions': 0.7,
        'sexual': 0.7,
        'sexual/minors': 0.7,
        'violence': 0.7,
        'violence/graphic': 0.7,
    }

    # Moderation levels with predefined thresholds
    MODERATION_LEVELS = {
        'strict': {
            'hate': 0.5,
            'hate/threatening': 0.4,
            'harassment': 0.5,
            'harassment/threatening': 0.4,
            'self-harm': 0.4,
            'self-harm/intent': 0.3,
            'self-harm/instructions': 0.3,
            'sexual': 0.5,
            'sexual/minors': 0.3,
            'violence': 0.5,
            'violence/graphic': 0.4,
        },
        'moderate': {
            'hate': 0.7,
            'hate/threatening': 0.6,
            'harassment': 0.7,
            'harassment/threatening': 0.6,
            'self-harm': 0.6,
            'self-harm/intent': 0.5,
            'self-harm/instructions': 0.5,
            'sexual': 0.7,
            'sexual/minors': 0.5,
            'violence': 0.7,
            'violence/graphic': 0.6,
        },
        'relaxed': {
            'hate': 0.85,
            'hate/threatening': 0.8,
            'harassment': 0.85,
            'harassment/threatening': 0.8,
            'self-harm': 0.8,
            'self-harm/intent': 0.75,
            'self-harm/instructions': 0.75,
            'sexual': 0.85,
            'sexual/minors': 0.7,
            'violence': 0.85,
            'violence/graphic': 0.8,
        }
    }

    def __init__(self):
        # Read API key from Django settings
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Get moderation level from settings
        self.moderation_level = getattr(settings, 'CONTENT_MODERATION_LEVEL', 'moderate')

        # Get custom thresholds from settings or use defaults
        if hasattr(settings, 'CONTENT_MODERATION_THRESHOLDS'):
            self.thresholds = settings.CONTENT_MODERATION_THRESHOLDS
        elif self.moderation_level in self.MODERATION_LEVELS:
            self.thresholds = self.MODERATION_LEVELS[self.moderation_level]
        else:
            self.thresholds = self.DEFAULT_THRESHOLDS

        logger.info(f"Content moderation initialized with level: {self.moderation_level}")

    def check_content(self, content, custom_thresholds=None):
        """
        Check if content contains harmful information with custom thresholds

        Args:
            content (str): Content to be moderated
            custom_thresholds (dict, optional): Custom thresholds for this check

        Returns:
            dict: Dictionary containing moderation results
                - flagged (bool): Whether content exceeds any threshold
                - categories (dict): Detection results for each category
                - category_scores (dict): Scores for each category (excluding None values)
                - exceeded_categories (list): Categories that exceeded thresholds

        Raises:
            Exception: Raised when API call fails
        """
        try:
            response = self.client.moderations.create(input=content)
            result = response.results[0]

            # Convert to dictionaries
            categories_dict = result.categories.model_dump() if hasattr(result.categories,
                                                                        'model_dump') else result.categories.dict()
            scores_dict = result.category_scores.model_dump() if hasattr(result.category_scores,
                                                                         'model_dump') else result.category_scores.dict()

            # Filter out None values and keep only valid scores
            valid_scores = {}
            for category, score in scores_dict.items():
                if score is not None and isinstance(score, (int, float)):
                    valid_scores[category] = score

            # Use custom thresholds if provided, otherwise use instance thresholds
            thresholds = custom_thresholds or self.thresholds

            # Check which categories exceed thresholds
            exceeded_categories = []
            flagged = False

            for category, score in valid_scores.items():
                threshold = thresholds.get(category, self.DEFAULT_THRESHOLDS.get(category, 0.7))
                if score >= threshold:
                    flagged = True
                    exceeded_categories.append({
                        'category': category,
                        'score': score,
                        'threshold': threshold
                    })

            return {
                'flagged': flagged,
                'categories': categories_dict,
                'category_scores': valid_scores,  # Only return valid scores
                'exceeded_categories': exceeded_categories,
                'moderation_level': self.moderation_level
            }
        except Exception as e:
            logger.error(f"Content moderation failed: {str(e)}")

            # Check if we should fail open or closed
            if getattr(settings, 'CONTENT_MODERATION_FAIL_OPEN', False):
                # Fail open - allow content when service is down
                logger.warning("Content moderation service unavailable, allowing content")
                return {
                    'flagged': False,
                    'categories': {},
                    'category_scores': {},
                    'exceeded_categories': [],
                    'moderation_level': self.moderation_level
                }
            else:
                # Fail closed - reject content when service is down
                raise serializers.ValidationError(
                    "Content moderation service temporarily unavailable, please try again later")

    def validate_content(self, content, custom_thresholds=None):
        """
        Validate if content is compliant based on thresholds

        Args:
            content (str): Content to validate
            custom_thresholds (dict, optional): Custom thresholds for this validation

        Raises:
            serializers.ValidationError: Raised when content exceeds thresholds
        """
        result = self.check_content(content, custom_thresholds)

        if result['flagged']:
            # Get the most severe violation
            if result['exceeded_categories']:
                most_severe = max(result['exceeded_categories'], key=lambda x: x['score'] - x['threshold'])
                category = most_severe['category']

                # Provide specific error messages
                error_messages = {
                    'hate': "Content contains hate speech",
                    'hate/threatening': "Content contains threatening hate speech",
                    'harassment': "Content contains harassment",
                    'harassment/threatening': "Content contains threatening harassment",
                    'self-harm': "Content contains self-harm references",
                    'self-harm/intent': "Content contains self-harm intent",
                    'self-harm/instructions': "Content contains self-harm instructions",
                    'sexual': "Content contains inappropriate sexual content",
                    'sexual/minors': "Content contains inappropriate content involving minors",
                    'violence': "Content contains violence",
                    'violence/graphic': "Content contains graphic violence",
                }

                error_msg = error_messages.get(category, "Content contains harmful material")

                # Add score information in debug mode
                if settings.DEBUG:
                    error_msg += f" (score: {most_severe['score']:.2f}, threshold: {most_severe['threshold']:.2f})"

                raise serializers.ValidationError(error_msg)

    def set_moderation_level(self, level):
        """
        Change moderation level at runtime

        Args:
            level (str): One of 'strict', 'moderate', 'relaxed'
        """
        if level in self.MODERATION_LEVELS:
            self.moderation_level = level
            self.thresholds = self.MODERATION_LEVELS[level]
            logger.info(f"Moderation level changed to: {level}")
        else:
            raise ValueError(f"Invalid moderation level: {level}. Choose from {list(self.MODERATION_LEVELS.keys())}")

    def set_threshold(self, category, threshold):
        """
        Set custom threshold for a specific category

        Args:
            category (str): Category name
            threshold (float): Threshold value (0.0 to 1.0)
        """
        if 0.0 <= threshold <= 1.0:
            self.thresholds[category] = threshold
            logger.info(f"Threshold for {category} set to {threshold}")
        else:
            raise ValueError("Threshold must be between 0.0 and 1.0")

    def get_current_settings(self):
        """Get current moderation settings"""
        return {
            'moderation_level': self.moderation_level,
            'thresholds': self.thresholds,
            'fail_open': getattr(settings, 'CONTENT_MODERATION_FAIL_OPEN', False)
        }


# Create global instance
content_moderation = ContentModerationService()