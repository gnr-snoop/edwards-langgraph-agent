import os
import re
from abc import ABC, abstractmethod
from google.oauth2 import service_account
from googleapiclient.discovery import build

class StorageServiceFactory:
    
    @staticmethod
    def create_storage_service_instance(type: str):
        if(type == "drive"):
            return DriveService()
        elif(type == "azure"):
            return AzureService()
        else:
            raise ValueError(f"storage service desconocido: {type}")

class StorageService(ABC):
    @abstractmethod
    def validate_permissions(self, documents, user_email) -> list:
        pass


class DriveService(StorageService):
    def __init__(self):
        self.credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not self.credentials_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        self.scopes = ["https://www.googleapis.com/auth/drive.readonly"]
        self.creds = service_account.Credentials.from_service_account_file(
            self.credentials_path, scopes=self.scopes
        )
        self.service = build("drive", "v3", credentials=self.creds)

    def validate_permissions(self, documents, user_email):
        """
        Validates user permissions for a list of documents by checking if the user's email matches
        any user-level permission for each document's Google Drive ID.

        For each document, extracts the Google Drive document ID from its source URL, then queries
        the Drive API to retrieve the document's permissions. If the user's email (local part only)
        matches any user permission, the document is added to the allowed list.

        Args:
            documents (list): A list of document objects, each containing a 'source' attribute.
            user_email (str): The email address of the user whose permissions are to be validated.

        Returns:
            list: A list of document objects for which the user has user-level permission.
        """

        if not documents:
            return []
        
        auth_required = os.environ.get('RAG_AUTH_REQUIRED') == 'true' 

        if not auth_required:
            return documents
        allowed_documents = []

        for document in documents:
            source = document.source
            pattern = r"(?<=d/)(.*?)(?=/edit|view)"
            document_id_match = re.findall(pattern, source)
            
            if document_id_match:
                document_id = document_id_match[0]
                permissions = self.service.permissions().list(
                    fileId=document_id, fields='permissions(type, emailAddress)'
                ).execute()

                for perm in permissions.get("permissions", []):
                    if perm.get("type") == "user":
                        email = perm["emailAddress"]
                        if email == user_email:
                            allowed_documents.append(document)
                            break 

        return allowed_documents

class AzureService(StorageService):
    def validate_permissions(self, documents, user_email):
        return documents
