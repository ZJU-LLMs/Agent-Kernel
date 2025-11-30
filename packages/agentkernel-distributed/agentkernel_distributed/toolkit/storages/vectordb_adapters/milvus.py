"""Milvus vector database adapter implementation."""

import asyncio
import time
from typing import Any, Dict, List, Optional, Sequence
from uuid import uuid4

from pymilvus import AsyncMilvusClient, CollectionSchema, DataType, FieldSchema

from ....toolkit.logger import get_logger
from ....toolkit.models.router import ModelRouter
from ....types.schemas.vectordb import VectorDocument, VectorSearchRequest, VectorSearchResult, VectorStoreInfo
from .base import BaseVectorDBAdapter

logger = get_logger(__name__)


class MilvusVectorAdapter(BaseVectorDBAdapter):
    """An asynchronous Milvus adapter.

    This adapter supports both standalone and clustered Milvus deployments and
    can handle custom document IDs. It can also automatically generate vector
    embeddings for documents and queries using a provided ModelRouter.

    Example for standalone mode:
        uri="http://host:19530"
    """

    def __init__(self):
        """Initializes the MilvusVectorAdapter."""
        self._config: Dict[str, Any] = {}
        self._client: Optional[AsyncMilvusClient] = None
        self._model_router: Optional[ModelRouter] = None
        self._embedding_model_name: Optional[str] = None
        self._vector_dim: Optional[int] = None

    @property
    def client(self) -> Optional[AsyncMilvusClient]:
        """The underlying AsyncMilvusClient instance."""
        return self._client

    async def connect(self, config: Dict[str, Any], model_router: Optional[ModelRouter] = None) -> None:
        """Connects to the Milvus server and initializes the collection.

        This method establishes a connection to Milvus, injects a ModelRouter
        for automatic embeddings, and ensures the specified collection exists.

        Args:
            config (Dict[str, Any]): The configuration dictionary for Milvus.
                Must include 'uri', 'collection_name', and either 'vector_dim'
                or 'embedding_model'.
            model_router (Optional[ModelRouter]): An instance of ModelRouter
                to handle embedding generation. Required if 'embedding_model'
                is specified in the config.

        Raises:
            RuntimeError: If the connection to Milvus fails, the vector
                dimension cannot be inferred, or the collection cannot be
                loaded.
            ValueError: If 'embedding_model' is provided without a
                ModelRouter, or if vector dimension cannot be determined.
        """
        if self._client:
            return

        self._config = config
        self._model_router = model_router
        self._embedding_model_name = self._config.get("embedding_model")
        if self._embedding_model_name and not self._model_router:
            logger.warning(
                "MilvusVectorAdapter is configured with an embedding_model, "
                "but no ModelRouter was provided at connect time."
            )

        if self._model_router and self._embedding_model_name:
            dummy_embedding = await self._model_router.embed("test", model_name=self._embedding_model_name)
            if dummy_embedding and isinstance(dummy_embedding, list):
                self._vector_dim = len(dummy_embedding)
                logger.info(
                    f"Inferred vector dimension {self._vector_dim} from " f"model '{self._embedding_model_name}'."
                )
            else:
                raise RuntimeError(
                    f"Could not infer vector dimension from embedding model " f"'{self._embedding_model_name}'."
                )
        elif "vector_dim" in self._config:
            self._vector_dim = self._config["vector_dim"]
            logger.warning(f"Using vector_dim from config: {self._vector_dim}.")
        else:
            raise ValueError(
                "Either 'vector_dim' or 'embedding_model' must be provided "
                "in the config to determine the vector dimension."
            )

        collection_name = self._config["collection_name"]
        try:
            self._client = AsyncMilvusClient(uri=config["uri"], token=config.get("token"))
            exists = await self._client.has_collection(collection_name)
            if not exists:
                await self._create_collection()
            await self._client.load_collection(collection_name)
        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to Milvus and ensure collection " f"'{collection_name}' is loaded: {e}"
            )

    async def disconnect(self) -> None:
        """Closes the connection to the Milvus server."""
        if self._client:
            await self._client.close()
            self._client = None

    async def is_connected(self) -> bool:
        """Checks if the adapter is currently connected to Milvus.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self._client is not None

    async def _ensure_connected(self) -> None:
        """Ensures there is an active connection to Milvus.

        Raises:
            ValueError: If the connection has not been configured via the
                `connect` method.
        """
        if self._client is None:
            if not self._config:
                raise ValueError("Connection config not set. Call connect() first.")
            await self.connect(self._config, self._model_router)

    async def _create_collection(self) -> None:
        """Creates the collection and required indexes in Milvus.

        The schema is defined based on the configuration, using the
        automatically inferred vector dimension.

        Raises:
            RuntimeError: If the vector dimension is unknown.
        """
        id_field_name = self._config.get("id_field_name", "doc_id")
        vector_field_name = self._config.get("vector_field_name", "embedding")
        timestamp_field_name = self._config.get("timestamp_field_name", "timestamp")
        tick_field_name = self._config.get("tick_field_name", "tick")
        if not self._vector_dim:
            raise RuntimeError("Cannot create collection, vector dimension is unknown.")

        schema = CollectionSchema(
            fields=[
                FieldSchema(name=id_field_name, dtype=DataType.VARCHAR, is_primary=True, max_length=128),
                FieldSchema(name=vector_field_name, dtype=DataType.FLOAT_VECTOR, dim=self._vector_dim),
                FieldSchema(name=timestamp_field_name, dtype=DataType.DOUBLE),
                FieldSchema(name=tick_field_name, dtype=DataType.INT64),
            ],
            enable_dynamic_field=True,
        )
        await self._client.create_collection(collection_name=self._config["collection_name"], schema=schema)

        index_params = self._client.prepare_index_params()
        index_params.add_index(
            field_name=vector_field_name,
            index_type=self._config.get("index_type", "IVF_FLAT"),
            metric_type=self._config.get("metric_type", "L2"),
            params=self._config.get("index_params", {"nlist": 128}),
        )
        index_params.add_index(field_name=timestamp_field_name, index_type="STL_SORT")
        index_params.add_index(field_name=tick_field_name, index_type="STL_SORT")
        await self._client.create_index(collection_name=self._config["collection_name"], index_params=index_params)

    async def upsert(self, documents: Sequence[VectorDocument], **kwargs: Any) -> List[str]:
        """Inserts or updates a batch of vector documents.

        If documents are provided without a vector but an embedding model is
        configured, their vectors will be generated automatically.

        Args:
            documents (Sequence[VectorDocument]): A sequence of documents to
                insert or update.
            **kwargs (Any): Additional parameters (not used).

        Returns:
            List[str]: A list of successfully processed document IDs.

        Raises:
            ValueError: If documents need embedding but no ModelRouter is
                configured.
            RuntimeError: If vector generation fails or returns a mismatched
                number of embeddings.
        """
        await self._ensure_connected()
        docs_to_embed = [doc for doc in documents if doc.vector is None]
        if docs_to_embed:
            if not self._model_router:
                raise ValueError("Documents require embedding, but no ModelRouter is " "configured.")

            contents = [doc.content for doc in docs_to_embed]
            logger.debug(f"Generating embeddings for {len(contents)} documents...")
            embeddings = await self._model_router.embed(contents, model_name=self._embedding_model_name)

            if embeddings and len(embeddings) == len(docs_to_embed):
                for doc, vector in zip(docs_to_embed, embeddings):
                    doc.vector = vector
            else:
                raise RuntimeError("Embedding generation failed or returned a mismatched " "number of vectors.")

        id_field = self._config.get("id_field_name", "doc_id")
        vector_field = self._config.get("vector_field_name", "embedding")
        timestamp_field = self._config.get("timestamp_field_name", "timestamp")
        tick_field = self._config.get("tick_field_name", "tick")
        entities = []
        final_ids = []
        for doc in documents:
            if doc.vector is None:
                logger.warning(f"Document '{doc.id or doc.content[:20]}' " "lacks a vector, skipping upsert.")
                continue

            doc_id = doc.id or str(uuid4())
            final_ids.append(doc_id)
            entity = dict(doc.metadata or {})
            entity[id_field] = doc_id
            entity[vector_field] = doc.vector
            entity["content"] = doc.content
            entity[timestamp_field] = time.time()
            entity[tick_field] = doc.tick
            entities.append(entity)

        if entities:
            await self._client.upsert(collection_name=self._config["collection_name"], data=entities)
        return final_ids

    async def delete(self, ids: Sequence[str], **kwargs: Any) -> bool:
        """Deletes documents based on a list of IDs.

        Args:
            ids (Sequence[str]): A sequence of document IDs to delete.
            **kwargs (Any): Additional parameters (not used).

        Returns:
            bool: True if the operation resulted in at least one deletion.
        """
        await self._ensure_connected()
        collection_name = self._config["collection_name"]

        res = await self._client.delete(collection_name=collection_name, ids=list(ids))

        delete_count = res.get("delete_count") or res.get("count", 0)
        return delete_count > 0

    async def search(self, request: VectorSearchRequest, **kwargs: Any) -> List[VectorSearchResult]:
        """Performs a similarity search with optional pre-filtering.

        If the query is a string, it will be automatically converted to a
        vector using the configured embedding model. If a filter string is
        provided in the request, it will be applied before the vector search.

        Args:
            request (VectorSearchRequest): A search request object containing
                the query, parameters, and an optional filter expression string.
            **kwargs (Any): Additional parameters (not used).

        Returns:
            List[VectorSearchResult]: A list of search results, sorted by
            similarity.

        Raises:
            ValueError: If the query is text but no ModelRouter is configured.
            RuntimeError: If embedding generation for the query fails.
            TypeError: If the query type is not a string or a list of floats.
        """
        await self._ensure_connected()
        query_vector: Optional[List[float]] = None
        if isinstance(request.query, str):
            if not self._model_router:
                raise ValueError("Query is text, but no ModelRouter is configured.")

            logger.debug(f"Generating embedding for query '{request.query[:30]}...'")
            embedding_result = await self._model_router.embed(request.query, model_name=self._embedding_model_name)
            if not embedding_result:
                raise RuntimeError("Failed to generate embedding for the query text.")
            query_vector = embedding_result
        elif isinstance(request.query, list):
            query_vector = request.query
        else:
            raise TypeError("VectorSearchRequest.query must be a string or a list of floats.")

        filter_expr = request.filter or ""
        if filter_expr:
            logger.debug(f"Applying search filter: {filter_expr}")

        id_field = self._config.get("id_field_name", "doc_id")
        vector_field = self._config.get("vector_field_name", "embedding")
        timestamp_field = self._config.get("timestamp_field_name", "timestamp")
        tick_field = self._config.get("tick_field_name", "tick")
        output_fields = ["*", vector_field]
        res = await self._client.search(
            collection_name=self._config["collection_name"],
            data=[query_vector],
            limit=request.top_k,
            filter=filter_expr,
            search_params=self._config.get("search_params"),
            output_fields=output_fields,
        )

        results: List[VectorSearchResult] = []
        for hit in res[0]:
            entity = hit.get("entity", {}).copy()
            doc_id = entity.pop(id_field, None)
            doc_vector = entity.pop(vector_field, [])
            doc_content = entity.pop("content", "")
            doc_timestamp = entity.pop(timestamp_field, None)
            doc_tick = entity.pop(tick_field, -1)  # Default to -1 if tick is missing
            doc = VectorDocument(
                id=doc_id,
                tick=doc_tick,
                content=doc_content,
                vector=doc_vector,
                metadata=entity,
                timestamp=doc_timestamp,
            )
            results.append(VectorSearchResult(document=doc, score=hit.get("distance")))
        return results

    async def retrieve_by_id(self, ids: Sequence[str], **kwargs: Any) -> List[VectorDocument]:
        """Retrieves one or more vector documents by their exact IDs.

        Args:
            ids (Sequence[str]): A sequence of document IDs to retrieve.
            **kwargs (Any): Additional parameters (not used).

        Returns:
            List[VectorDocument]: A list of the found vector documents.
        """
        await self._ensure_connected()

        res = await self._client.get(collection_name=self._config["collection_name"], ids=list(ids))

        docs = []
        id_field = self._config.get("id_field_name", "doc_id")
        vector_field = self._config.get("vector_field_name", "embedding")
        timestamp_field = self._config.get("timestamp_field_name", "timestamp")
        tick_field = self._config.get("tick_field_name", "tick")
        for entity in res:
            doc_id = entity.pop(id_field, None)
            vector = entity.pop(vector_field, [])
            doc_content = entity.pop("content", "")
            doc_timestamp = entity.pop(timestamp_field, None)
            doc_tick = entity.pop(tick_field, -1)  # Default to -1 if tick is missing

            docs.append(
                VectorDocument(
                    id=doc_id,
                    tick=doc_tick,
                    vector=vector,
                    content=doc_content,
                    metadata=entity,
                    timestamp=doc_timestamp,
                )
            )
        return docs

    async def get_info(self) -> VectorStoreInfo:
        """Gets status information about the vector store.

        Returns:
            VectorStoreInfo: A status object containing the document count and
            vector dimensions.
        """
        await self._ensure_connected()
        stats = await self._client.get_collection_stats(
            collection_name=self._config["collection_name"],
        )
        doc_count = int(stats.get("row_count", 0))
        return VectorStoreInfo(
            doc_count=doc_count,
            vector_dim=self._vector_dim,
        )

    async def clear(self) -> bool:
        """Deletes and recreates the collection, effectively clearing all data.

        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        try:
            await self._ensure_connected()
            collection_name = self._config["collection_name"]
            await self._client.drop_collection(collection_name)
            await self._create_collection()
            await self._client.load_collection(collection_name)
            return True
        except Exception:
            return False

    async def search_for_metadata(self, query_vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        """A convenience method to search by vector and return only metadata.

        Args:
            query_vector (List[float]): The query vector.
            top_k (int): The number of results to return.

        Returns:
            List[Dict[str, Any]]: A list of metadata from the matched
            documents.
        """
        request = VectorSearchRequest(query=query_vector, top_k=top_k)
        results = await self.search(request)
        return [res.document.metadata for res in results if res.document.metadata]

    async def retrieve_outdated_documents(self, older_than_timestamp: float) -> List[VectorDocument]:
        """Retrieves documents older than a given timestamp.

        Args:
            older_than_timestamp (float): A Unix timestamp. All documents with
                an earlier timestamp will be retrieved.

        Returns:
            List[VectorDocument]: A list of outdated documents.
        """
        await self._ensure_connected()

        collection_name = self._config["collection_name"]
        id_field = self._config.get("id_field_name", "doc_id")
        vector_field = self._config.get("vector_field_name", "embedding")
        timestamp_field = self._config.get("timestamp_field_name", "timestamp")
        tick_field = self._config.get("tick_field_name", "tick")
        filter_expr = f"{timestamp_field} < {older_than_timestamp}"

        query_results = await self._client.query(
            collection_name=collection_name, filter=filter_expr, output_fields=["*"]
        )

        outdated_docs = []
        for entity in query_results:
            doc_id = entity.pop(id_field, None)
            vector = entity.pop(vector_field, [])
            doc_content = entity.pop("content", "")
            doc_timestamp = entity.pop(timestamp_field, None)
            doc_tick = entity.pop(tick_field, -1)
            outdated_docs.append(
                VectorDocument(
                    id=doc_id,
                    tick=doc_tick,
                    vector=vector,
                    content=doc_content,
                    metadata=entity,
                    timestamp=doc_timestamp,
                )
            )

        return outdated_docs

    async def delete_outdated_documents(self, older_than_timestamp: float) -> int:
        """Deletes documents older than a given timestamp.

        Args:
            older_than_timestamp (float): A Unix timestamp. All documents with
                an earlier timestamp will be deleted.

        Returns:
            int: The number of documents deleted.
        """
        await self._ensure_connected()
        timestamp_field = self._config.get("timestamp_field_name", "timestamp")
        filter_expr = f"{timestamp_field} < {older_than_timestamp}"

        res = await self._client.delete(collection_name=self._config["collection_name"], filter=filter_expr)

        delete_count = res.get("delete_count") or res.get("count", 0)
        return delete_count

    async def undo(self, tick: int) -> bool:
        """Deletes all documents created strictly after the specified tick.

        This effectively "undos" all changes made after a certain point,
        reverting the collection to the state it was in at the specified tick.

        Args:
            tick (int): The reference tick. All documents with a tick
                strictly greater than this value will be deleted.

        Returns:
            bool: True if the operation was successful (even if 0 docs
                  were deleted), False if an error occurred.
        """
        try:
            await self._ensure_connected()

            tick_field = self._config.get("tick_field_name", "tick")
            collection_name = self._config["collection_name"]

            filter_expr = f"{tick_field} > {tick}"

            logger.info(
                f"Performing undo on collection '{collection_name}'. " f"Deleting documents with filter: {filter_expr}"
            )

            res = await self._client.delete(collection_name=collection_name, filter=filter_expr)

            delete_count = res.get("delete_count") or res.get("count", 0)
            logger.info(f"Undo operation complete. Deleted {delete_count} documents.")

            return True

        except Exception as e:
            logger.error(
                f"Failed to perform undo operation on collection " f"'{self._config.get('collection_name')}': {e}"
            )
            return False

    async def import_data(self, data: List[VectorDocument]) -> None:
        """Imports a list of documents into the collection.

        This is an alias for the `upsert` method.

        Args:
            data (List[VectorDocument]): The list of documents to import.
        """
        await self.upsert(documents=data)

    async def export_data(self, page_size: int = 1000, **kwargs: Any) -> List[VectorDocument]:
        """Exports all document data from the vector store.

        This operation paginates through the entire collection to retrieve
        all documents.

        Args:
            page_size (int): The number of documents to fetch per page.
            **kwargs (Any): Other backend-specific parameters (not used).

        Returns:
            List[VectorDocument]: A list containing all documents in the store.
        """
        await self._ensure_connected()
        collection_name = self._config["collection_name"]
        id_field = self._config.get("id_field_name", "doc_id")
        vector_field = self._config.get("vector_field_name", "embedding")
        timestamp_field = self._config.get("timestamp_field_name", "timestamp")
        tick_field = self._config.get("tick_field_name", "tick")
        output_fields = ["*"]
        all_docs: List[VectorDocument] = []
        offset = 0
        while True:
            page_results = await self._client.query(
                collection_name=collection_name, filter="", limit=page_size, offset=offset, output_fields=output_fields
            )
            if not page_results:
                break
            for entity in page_results:
                doc_id = entity.pop(id_field, None)
                vector = entity.pop(vector_field, [])
                doc_content = entity.pop("content", "")
                doc_timestamp = entity.pop(timestamp_field, None)
                doc_tick = entity.pop(tick_field, -1)
                all_docs.append(
                    VectorDocument(
                        id=doc_id,
                        tick=doc_tick,
                        vector=vector,
                        content=doc_content,
                        metadata=entity,
                        timestamp=doc_timestamp,
                    )
                )
            offset += len(page_results)
            if len(page_results) < page_size:
                break
        return all_docs
