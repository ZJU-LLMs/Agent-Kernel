"""Schemas for vector database documents and operations."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel


class VectorDocument(BaseModel):
    """Represents a document containing a vector.

    Attributes:
        id (Optional[str]): The unique identifier for the document. If None,
            it will be generated automatically upon insertion.
        tick (int): Current tick when the document is upserted.
        content (str): The original text content of the document, which is
            the source for vectorization.
        timestamp (Optional[float]): The timestamp when the document was added
            to the database, generated automatically upon insertion.
        vector (Optional[List[float]]): The vector representation of the
            document. Becomes optional as it can be generated from content.
        metadata (Optional[Dict[str, Any]]): Additional metadata for storing
            extra information.
    """

    id: Optional[str] = None
    tick: int
    content: str
    timestamp: Optional[float] = None
    vector: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None


class VectorSearchRequest(BaseModel):
    """Encapsulates a vector similarity search request.

    Attributes:
        query (Union[str, List[float]]): The vector or text to use for the query.
        top_k (int): The number of most similar results to return.
        filter (Optional[str]): A Milvus-compatible filter expression string
            (e.g., 'genre == "sci-fi" and year > 2020').
    """

    query: Union[str, List[float]]
    top_k: int = 3
    filter: Optional[str] = None


class VectorSearchResult(BaseModel):
    """Represents a single hit from a vector search.

    Attributes:
        document (VectorDocument): The matching vector document.
        score (float): The similarity or distance score. A higher score
            typically indicates greater similarity, depending on the
            implementation.
    """

    document: VectorDocument
    score: float


class VectorStoreInfo(BaseModel):
    """Describes the status information of the vector store.

    Attributes:
        doc_count (int): The total number of documents in the store.
        vector_dim (int): The dimension of the vectors stored.
    """

    doc_count: int
    vector_dim: int
