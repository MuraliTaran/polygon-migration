import logging
import os
from django.conf import settings
from azure.identity import UsernamePasswordCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError, ClientAuthenticationError
from ..interfaces.storage import StorageProvider

logger = logging.getLogger(__name__)

class AzureStorageProvider(StorageProvider):
    """
    Storage provider implementation for Azure Blob Storage.
    Reads credentials from Django settings.
    """
    
    def __init__(self):
        self.account_url = settings.AZURE_STORAGE_ACCOUNT_URL
        self.container_name = settings.AZURE_CONTAINER_NAME
        
        tenant_id = settings.AZURE_TENANT_ID
        client_id = settings.AZURE_CLIENT_ID
        username = settings.AZURE_USERNAME
        password = settings.AZURE_PASSWORD
        
        self.blob_service_client = None

        logger.info("Initializing AzureStorageProvider...")
        try:
            credential = UsernamePasswordCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                username=username,
                password=password
            )
            self.blob_service_client = BlobServiceClient(
                account_url=self.account_url, 
                credential=credential
            )
            # Verify container exists or create it? 
            # Current implementation assumes it exists. We can leave it as is.
            
            logger.info("Azure authentication successful.")
        except ClientAuthenticationError as e:
            logger.error(f"Azure Authentication Failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Azure Initialization Error: {e}")
            raise

    def upload(self, path: str, content: bytes) -> None:
        """
        Uploads content as a blob to the configured container.
        Args:
            path: Blob name (e.g. 'test_cases/1/01')
            content: Bytes content to upload
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=path
            )
            blob_client.upload_blob(content, overwrite=True)
            logger.info(f"Azure Upload: Uploaded to {path}")
        except Exception as e:
            logger.error(f"Azure Upload Error for {path}: {e}")
            raise

    def delete_by_prefix(self, prefix: str) -> None:
        """
        Deletes all blobs starting with prefix in the configured container.
        """
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            # List blobs starting with the prefix
            blobs_to_delete = container_client.list_blobs(name_starts_with=prefix)
            
            # Using list comprehension to exhaust the iterator if not already a list
            # But list_blobs returns an ItemPaged which is iterable.
            # We must iterate and delete.
            
            count = 0
            for blob in blobs_to_delete:
                container_client.delete_blob(blob.name)
                count += 1
            
            logger.info(f"Azure Delete: Deleted {count} blobs starting with {prefix}")
        except Exception as e:
            logger.error(f"Azure Delete Error for prefix {prefix}: {e}")
            raise
