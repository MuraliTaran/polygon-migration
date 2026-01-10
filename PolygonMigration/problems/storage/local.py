import os
import shutil
import logging
from django.conf import settings
from ..interfaces.storage import StorageProvider

logger = logging.getLogger(__name__)

class LocalStorageProvider(StorageProvider):
    """
    Storage provider that saves files to the local filesystem.
    Files are stored under a 'media' directory in the project root.
    """

    def __init__(self):
        # Determine the base path for local storage
        # We use a 'media' folder in the base directory
        self.base_path = os.path.join(settings.BASE_DIR, 'media')
        
        # Ensure the directory exists
        if not os.path.exists(self.base_path):
            try:
                os.makedirs(self.base_path)
                logger.info(f"Created local storage directory at: {self.base_path}")
            except OSError as e:
                logger.error(f"Failed to create local storage directory: {e}")
                raise

    def upload(self, path: str, content: bytes) -> None:
        """
        Saves the content to a file on the local disk.
        """
        full_path = os.path.join(self.base_path, path)
        directory = os.path.dirname(full_path)

        try:
            if not os.path.exists(directory):
                os.makedirs(directory)

            with open(full_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"Local Storage: Saved {path}")
        except Exception as e:
            logger.error(f"Local Storage Error saving {path}: {e}")
            raise

    def delete_by_prefix(self, prefix: str) -> None:
        """
        Deletes the directory corresponding to the prefix if it exists.
        For test cases, the prefix usually corresponds to a folder like 'test_cases/{id}/'.
        """
        target_path = os.path.join(self.base_path, prefix)

        try:
            # If it's a directory, remove the whole tree
            if os.path.isdir(target_path):
                shutil.rmtree(target_path)
                logger.info(f"Local Storage: Deleted directory {prefix}")
            # If it's a file, remove the file
            elif os.path.isfile(target_path):
                os.remove(target_path)
                logger.info(f"Local Storage: Deleted file {prefix}")
            else:
                logger.warning(f"Local Storage: Path not found for deletion: {target_path}")
        except Exception as e:
            logger.error(f"Local Storage Error deleting {prefix}: {e}")
