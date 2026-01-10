import os
import shutil
import unittest
import logging
from django.conf import settings
from django.test import SimpleTestCase, override_settings
from problems.storage.local import LocalStorageProvider

# Disable Logging for clean output
# logging.disable(logging.CRITICAL)

# Configure logging
logging.basicConfig(
    filename='logs/test.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TestLocalStorage')

class TestLocalStorage(SimpleTestCase):
    
    def setUp(self):
        logger.info("Setting up LocalStorage test")
        # Setup a temporary media root for testing
        self.test_media_root = os.path.join(settings.BASE_DIR, 'test_media_temp')
        self.provider = LocalStorageProvider()
        # Hack path to force testing against temp dir
        self.provider.base_path = self.test_media_root

    def tearDown(self):
        # Cleanup created files
        logger.info("Tearing down LocalStorage test")
        if os.path.exists(self.test_media_root):
             shutil.rmtree(self.test_media_root)

    def test_upload(self):
        logger.info("Testing LocalStorage upload")
        path = "test_folder/file.txt"
        content = b"Hello Local Storage"
        
        self.provider.upload(path, content)
        
        full_path = os.path.join(self.test_media_root, path)
        self.assertTrue(os.path.exists(full_path))
        with open(full_path, 'rb') as f:
            self.assertEqual(f.read(), content)
        logger.info("LocalStorage upload verified")

    def test_delete_by_prefix(self):
        logger.info("Testing LocalStorage delete_by_prefix")
        # create duplicate files
        self.provider.upload("folder/1.txt", b"data")
        self.provider.upload("folder/2.txt", b"data")
        
        self.assertTrue(os.path.exists(os.path.join(self.test_media_root, "folder/1.txt")))
        
        self.provider.delete_by_prefix("folder/")
        
        self.assertFalse(os.path.exists(os.path.join(self.test_media_root, "folder/1.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.test_media_root, "folder")))
        logger.info("LocalStorage delete_by_prefix verified")
