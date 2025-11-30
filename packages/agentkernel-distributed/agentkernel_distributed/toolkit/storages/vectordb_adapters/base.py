"""Base class for asynchronous vector database adapters."""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Sequence

from ....types.schemas.vectordb import VectorDocument, VectorSearchRequest, VectorSearchResult, VectorStoreInfo
from ..base import DatabaseAdapter


class BaseVectorDBAdapter(DatabaseAdapter):
    """A common base class for all asynchronous vector database adapters.

    This class inherits from `DatabaseAdapter` and defines the asynchronous
    interface specific to vector stores.
    """

    @abstractmethod
    async def upsert(self, documents: Sequence[VectorDocument], **kwargs: Any) -> List[str]:
        """Inserts or updates a batch of vector documents.

        Args:
            documents (Sequence[VectorDocument]): A sequence of documents to
                insert or update.
            **kwargs (Any): Additional parameters specific to the backend
                implementation.

        Returns:
            List[str]: A list of successfully processed document IDs.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, ids: Sequence[str], **kwargs: Any) -> bool:
        """Deletes documents based on a list of IDs.

        Args:
            ids (Sequence[str]): A sequence of document IDs to delete.
            **kwargs (Any): Additional parameters specific to the backend
                implementation.

        Returns:
            bool: True if the operation was successful.
        """
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        request: VectorSearchRequest,
        **kwargs: Any,
    ) -> List[VectorSearchResult]:
        """Performs a similarity search.

        Args:
            request (VectorSearchRequest): A search request object containing
                the query vector and parameters.
            **kwargs (Any): Additional parameters specific to the backend
                implementation.

        Returns:
            List[VectorSearchResult]: A list of search results, sorted by
            similarity.
        """
        raise NotImplementedError

    @abstractmethod
    async def retrieve_by_id(self, ids: Sequence[str], **kwargs: Any) -> List[VectorDocument]:
        """Retrieves one or more vector documents by their exact IDs.

        Args:
            ids (Sequence[str]): A sequence of document IDs to retrieve.
            **kwargs (Any): Additional parameters specific to the backend
                implementation.

        Returns:
            List[VectorDocument]: A list of the found vector documents.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_info(self) -> VectorStoreInfo:
        """Gets status information about the vector store.

        Returns:
            VectorStoreInfo: A status object containing the document count and
            vector dimensions.
        """
        raise NotImplementedError

    @abstractmethod
    async def export_data(self, page_size: int = 1000, **kwargs: Any) -> List[VectorDocument]:
        """Exports all document data from the vector store.

        This operation is typically handled internally with pagination due to
        the potentially large volume of data.

        Args:
            page_size (int): The number of documents to fetch per page during
                internal queries.
            **kwargs (Any): Other backend-specific parameters.

        Returns:
            List[VectorDocument]: A list containing all documents in the store.
        """
        raise NotImplementedError
