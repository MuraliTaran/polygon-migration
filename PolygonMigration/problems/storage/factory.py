from django.conf import settings
from ..interfaces.storage import StorageProvider
from .local import LocalStorageProvider
from .azure import AzureStorageProvider
from .gdrive import GoogleDriveStorageProvider
from .gcs import GoogleCloudStorageProvider
import logging

logger = logging.getLogger(__name__)

def get_storage_provider() -> StorageProvider:
    """
    Factory function to return the configured StorageProvider.
    Defaults to LocalStorageProvider if STORAGE_PROVIDER is not set or unknown.
    """
    provider_type = getattr(settings, 'STORAGE_PROVIDER', 'LOCAL').upper()
    
    logger.info(f"Storage Factory: initializing provider '{provider_type}'")
    
    if provider_type == 'AZURE':
        return AzureStorageProvider()
    elif provider_type == 'GDRIVE':
        return GoogleDriveStorageProvider()
    elif provider_type == 'GCS':
        return GoogleCloudStorageProvider()
    elif provider_type == 'LOCAL':
        return LocalStorageProvider()
    else:
        logger.warning(f"Unknown STORAGE_PROVIDER '{provider_type}', falling back to LOCAL.")
        return LocalStorageProvider()
