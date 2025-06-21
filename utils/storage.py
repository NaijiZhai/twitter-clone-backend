from storages.backends.s3boto3 import S3Boto3Storage
from botocore.exceptions import ClientError
from io import BytesIO
import logging
import hashlib
import time
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


class CustomS3Storage(S3Boto3Storage):
    def _save(self, name, content):
        """
        Override _save to handle Content-Length issues with proxied S3 connections
        """
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Ensure content is at the beginning
                if hasattr(content, 'seek'):
                    content.seek(0)

                # Read the entire content into memory to ensure accurate Content-Length
                if hasattr(content, 'read'):
                    content_data = content.read()

                    # Create a new ContentFile with the exact data
                    new_content = ContentFile(content_data)

                    # Preserve important attributes
                    if hasattr(content, 'content_type'):
                        new_content.content_type = content.content_type
                    if hasattr(content, 'name'):
                        new_content.name = content.name

                    # Explicitly set the size
                    new_content.size = len(content_data)

                    # Use the new content for saving
                    return super()._save(name, new_content)
                else:
                    return super()._save(name, content)

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                logger.warning(f"S3 upload attempt {retry_count + 1} failed for {name}: {error_code}")

                if error_code == 'IncompleteBody' and retry_count < max_retries - 1:
                    retry_count += 1
                    # Add a small delay before retrying
                    time.sleep(0.5 * retry_count)

                    # Reset content position for retry
                    if hasattr(content, 'seek'):
                        content.seek(0)
                    continue
                else:
                    logger.error(f"S3 ClientError after {retry_count + 1} attempts: {e}")
                    raise

            except Exception as e:
                logger.error(f"Unexpected error during file save: {e}")
                raise

        # If we get here, all retries failed
        raise Exception(f"Failed to upload {name} after {max_retries} attempts")

    def _open(self, name, mode='rb'):
        """
        Override _open to handle any read issues through the proxy
        """
        try:
            return super()._open(name, mode)
        except ClientError as e:
            logger.error(f"Error opening file {name}: {e}")
            raise

    def url(self, name):
        """
        Override url to ensure consistent URL generation
        """
        try:
            return super().url(name)
        except Exception as e:
            logger.error(f"Error generating URL for {name}: {e}")
            # Return a fallback URL if possible
            if hasattr(self, 'endpoint_url') and self.endpoint_url:
                return f"{self.endpoint_url}/{self.bucket_name}/{name}"
            raise