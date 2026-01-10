import os
import io
import logging
import json
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from ..interfaces.storage import StorageProvider

logger = logging.getLogger(__name__)

class GoogleDriveStorageProvider(StorageProvider):
    """
    Storage provider implementation for Google Drive.
    Uses a Service Account for authentication.
    """

    SCOPES = ['https://www.googleapis.com/auth/drive']

    def __init__(self):
        self.credentials_file = settings.GOOGLE_DRIVE_CREDENTIALS_FILE
        self.root_folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
        
        if not self.credentials_file or not os.path.exists(self.credentials_file):
            raise Exception("Google Drive credentials file not found or not configured.")
        
        # Determine authentication type based on JSON content
        with open(self.credentials_file) as f:
            cred_data = json.load(f)
        
        if 'type' in cred_data and cred_data['type'] == 'service_account':
            self._init_service_account(self.credentials_file)
        else:
            self._init_oauth_client(self.credentials_file)

    def _init_service_account(self, cred_file):
        try:
            creds = service_account.Credentials.from_service_account_file(
                cred_file, scopes=self.SCOPES)
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Google Drive Service initialized (Service Account).")
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service account: {e}")
            raise

    def _init_oauth_client(self, client_secret_file):
        """
        Initializes Google Drive service using OAuth 2.0 User Credentials.
        This allows using Personal Drive storage quota.
        """
        creds = None
        token_path = os.path.join(os.path.dirname(client_secret_file), 'token.json')

        # Load existing token if available
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
        
        # Refresh or Create new token
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                     # If refresh fails, re-auth
                     creds = None

            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file(
                    client_secret_file, self.SCOPES)
                # 'run_console' is deprecated/removed by Google (OOB flow).
                # We MUST use run_local_server. We force port 8080 to match the Google Console config.
                # User MUST add 'http://localhost:8080/' to Authorized Redirect URIs.
                creds = flow.run_local_server(port=8080)
            
            # Save the credentials for the next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        try:
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Google Drive Service initialized (User Credentials).")
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive user credentials: {e}")
            raise

    def _get_or_create_folder(self, folder_name, parent_id):
        """
        Helper to find a folder by name within a parent, or create it if missing.
        """
        query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.service.files().list(
            q=query, 
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        files = results.get('files', [])

        if files:
            return files[0]['id']
        else:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = self.service.files().create(
                body=file_metadata, 
                fields='id',
                supportsAllDrives=True
            ).execute()
            return folder.get('id')

    def _resolve_path_to_folder(self, path):
        """
        Resolves a path string (e.g. 'test_cases/101') to a folder ID.
        Creates folders if they don't exist.
        Returns tuple (parent_folder_id, file_name)
        """
        parts = path.strip('/').split('/')
        file_name = parts[-1]
        folder_path = parts[:-1]
        
        current_parent_id = self.root_folder_id
        for folder in folder_path:
            current_parent_id = self._get_or_create_folder(folder, current_parent_id)
            
        return current_parent_id, file_name

    def upload(self, path: str, content: bytes) -> None:
        """
        Uploads content as a file to Google Drive, creating folder structure as needed.
        """
        try:
            parent_id, file_name = self._resolve_path_to_folder(path)
            
            # Check if file exists to update or create new
            query = f"name='{file_name}' and '{parent_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query, 
                fields="files(id)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            files = results.get('files', [])

            media = MediaIoBaseUpload(io.BytesIO(content), mimetype='application/octet-stream', resumable=True)

            if files:
                # Update existing file
                file_id = files[0]['id']
                self.service.files().update(
                    fileId=file_id, 
                    media_body=media,
                    supportsAllDrives=True
                ).execute()
                logger.info(f"Google Drive: Updated file {path} (ID: {file_id})")
            else:
                # Create new file
                file_metadata = {'name': file_name, 'parents': [parent_id]}
                new_file = self.service.files().create(
                    body=file_metadata, 
                    media_body=media, 
                    fields='id',
                    supportsAllDrives=True
                ).execute()
                logger.info(f"Google Drive: Created file {path} (ID: {new_file.get('id')})")
                
        except Exception as e:
            logger.error(f"Google Drive Upload Error for {path}: {e}")
            raise

    def delete_by_prefix(self, prefix: str) -> None:
        """
        Deletes the directory corresponding to the prefix.
        Expects prefix to be a folder path string ending in '/' e.g., 'test_cases/101/'
        """
        try:
            # We assume the prefix maps to a folder structure
            # Logic: resolve the path up to the last folder and delete that folder
            folder_path = prefix.strip('/')
            parts = folder_path.split('/')
            
            # Find the target folder
            current_parent_id = self.root_folder_id
            target_id = None
            
            for i, part in enumerate(parts):
                query = f"name='{part}' and '{current_parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                results = self.service.files().list(
                    q=query, 
                    fields="files(id)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
                files = results.get('files', [])
                
                if not files:
                    logger.warning(f"Google Drive: path {prefix} not found, nothing to delete.")
                    return
                
                current_parent_id = files[0]['id']
                if i == len(parts) - 1:
                    target_id = current_parent_id

            if target_id:
                # Delete the folder and all contents
                self.service.files().delete(fileId=target_id, supportsAllDrives=True).execute()
                logger.info(f"Google Drive: Deleted folder {prefix} (ID: {target_id})")

        except Exception as e:
            logger.error(f"Google Drive Delete Error for {prefix}: {e}")
            raise
