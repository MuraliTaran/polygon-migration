import os
import logging
from django.conf import settings
from google.cloud import storage
from ..interfaces.storage import StorageProvider

logger = logging.getLogger(__name__)

class GoogleCloudStorageProvider(StorageProvider):
    """
    Storage provider implementation for Google Cloud Storage (GCS).
    Uses a Service Account JSON file for authentication.
    """

    def __init__(self):
        self.credentials_file = settings.GCS_CREDENTIALS_FILE
        self.bucket_name = settings.GCS_BUCKET_NAME
        self.project_id = settings.GCS_PROJECT_ID

        if not self.credentials_file or not os.path.exists(self.credentials_file):
            raise Exception("GCS credentials file not found or not configured.")
            
        if not self.bucket_name:
             raise Exception("GCS_BUCKET_NAME is not configured.")

        try:
            # Initialize the client with the service account credentials
            self.client = storage.Client.from_service_account_json(self.credentials_file)
            self.bucket = self.client.bucket(self.bucket_name)
            
            # Simple check if bucket exists or we have access
            if not self.bucket.exists():
                logger.warning(f"GCS Bucket '{self.bucket_name}' does not exist or is not accessible. Attempting to create...")
                # Note: Creating buckets requires special permissions (Project Editor/Storage Admin)
                # If using a restricted service account, create the bucket manually in Cloud Console first.
                self.bucket = self.client.create_bucket(self.bucket_name)
            
            logger.info(f"GCS Service initialized successfully. Bucket: {self.bucket_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize GCS service: {e}")
            raise

    def upload(self, path: str, content: bytes) -> None:
        """
        Uploads content as a blob to GCS.
        path: 'test_cases/1/12' -> saved as object 'test_cases/1/12'
        """
        try:
            # Remove leading slashes for object names in buckets
            blob_path = path.lstrip('/')
            blob = self.bucket.blob(blob_path)
            
            blob.upload_from_string(content, content_type='application/octet-stream')
            
            logger.info(f"GCS: Uploaded file {blob_path}")
                
        except Exception as e:
            logger.error(f"GCS Upload Error for {path}: {e}")
            raise

    def delete_by_prefix(self, prefix: str) -> None:
        """
        Deletes all blobs handling the prefix.
        Expects prefix to be like 'test_cases/101/'
        """
        try:
            clean_prefix = prefix.lstrip('/')
            blobs = list(self.client.list_blobs(self.bucket, prefix=clean_prefix))
            
            if not blobs:
                logger.warning(f"GCS: path {clean_prefix} not found or empty, nothing to delete.")
                return

            # Batch delete is more efficient
            self.bucket.delete_blobs(blobs)
            logger.info(f"GCS: Deleted {len(blobs)} files with prefix {clean_prefix}")

        except Exception as e:
            logger.error(f"GCS Delete Error for {prefix}: {e}")
            raise
