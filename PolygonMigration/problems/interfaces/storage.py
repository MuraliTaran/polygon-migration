from abc import ABC, abstractmethod

class StorageProvider(ABC):
    """
    Abstract base class defining the contract for storage operations.
    This ensures functionality can be swapped between Azure, AWS, and Local Storage.
    """

    @abstractmethod
    def upload(self, path: str, content: bytes) -> None:
        """
        Uploads content to the specified path.

        Args:
            path (str): Relative path ensuring unique identification (e.g., 'test_cases/101/01').
            content (bytes): The binary content to be stored.
        """
        pass

    @abstractmethod
    def delete_by_prefix(self, prefix: str) -> None:
        """
        Deletes all files/objects that start with the given prefix.
        Used to clean up old test cases before a new migration.

        Args:
            prefix (str): The common prefix for the objects to delete (e.g., 'test_cases/101/').
        """
        pass
