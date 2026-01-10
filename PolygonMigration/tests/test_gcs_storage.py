import os
import unittest
import logging
from django.conf import settings
from django.test import SimpleTestCase
from problems.storage.gcs import GoogleCloudStorageProvider

# Configure logging
logging.basicConfig(
    filename='logs/test.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TestGCSStorage')

# Skip if GCS not configured
@unittest.skipIf(not os.getenv('GCS_CREDENTIALS_FILE'), "GCS Credentials not found")
class TestGCSStorage(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            logger.info("Initializing GCS Provider")
            cls.provider = GoogleCloudStorageProvider()
        except Exception as e:
            logger.error(f"Failed to initialize GCS provider: {e}")
            cls.provider = None

    def setUp(self):
        if not self.provider:
            self.skipTest("GCS Provider failed to initialize")
        logger.info("Setting up GCS test")

    def test_upload_and_delete(self):
        test_path = "integration_test/gcs_status.txt"
        test_content = b"Integration Test for GCS"
        
        logger.info(f"Uploading {test_path} to GCS")
        print(f"\n[GCS] Uploading {test_path}...")
        self.provider.upload(test_path, test_content)
        
        # Verify blob exists
        blob = self.provider.bucket.blob(test_path)
        exists = blob.exists()
        if exists:
            logger.info("GCS upload successful, blob exists")
        else:
            logger.error("GCS upload failed, blob does not exist")
        self.assertTrue(exists, "Blob was not uploaded to GCS")
        
        # Read content back
        downloaded = blob.download_as_bytes()
        self.assertEqual(downloaded, test_content)
        
        # Test Delete
        logger.info(f"Deleting prefix integration_test/ from GCS")
        print(f"[GCS] Deleting prefix integration_test/...")
        self.provider.delete_by_prefix("integration_test/")
        
        self.assertFalse(blob.exists(), "Blob should have been deleted")
        logger.info("GCS delete successful")
