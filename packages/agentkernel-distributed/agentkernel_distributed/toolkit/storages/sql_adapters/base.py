"""Base class for asynchronous SQL database adapters."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Sequence, Tuple
from ..base import DatabaseAdapter


class BaseSQLAdapter(DatabaseAdapter):
    """
    Universal abstract base class for all asynchronous relational database adapters.

    Defines a standard set of CRUD (Create, Read, Update, Delete) and schema management interfaces.
    """

    @abstractmethod
    async def table_exists(self, table_name: str) -> bool:
        """
        Checks if the specified table exists.

        Args:
            table_name (str): The name of the table.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def create_table(
        self, table_name: str, columns: Dict[str, str], primary_key: Optional[str] = None, if_not_exists: bool = True
    ) -> None:
        """
        Creates a new table.

        Args:
            table_name (str): The name of the table.
            columns (Dict[str, str]): A mapping of column names to data types (e.g., {"id": "SERIAL", "name": "VARCHAR(255)"}).
            primary_key (Optional[str]): The name of the primary key column.
            if_not_exists (bool): If True, adds an "IF NOT EXISTS" clause.
        """
        raise NotImplementedError

    @abstractmethod
    async def drop_table(self, table_name: str, if_exists: bool = True) -> None:
        """
        Deletes a table.

        Args:
            table_name (str): The name of the table to delete.
            if_exists (bool): If True, adds an "IF EXISTS" clause.
        """
        raise NotImplementedError

    @abstractmethod
    async def insert(self, table_name: str, records: Sequence[Dict[str, Any]]) -> int:
        """
        Inserts one or more records into a table.

        Args:
            table_name (str): The name of the table.
            records (Sequence[Dict[str, Any]]): A sequence of record dictionaries.

        Returns:
            int: The number of successfully inserted records.
        """
        raise NotImplementedError

    @abstractmethod
    async def select(
        self,
        table_name: str,
        columns: Optional[Sequence[str]] = None,
        where: Optional[Tuple[str, Sequence[Any]]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Queries records from a table.

        Args:
            table_name (str): The name of the table.
            columns (Optional[Sequence[str]]): The columns to select; if None, selects all columns (*).
            where (Optional[Tuple[str, Sequence[Any]]]): A WHERE clause, formatted as ("id = $1 AND name = $2", [1, "John"]).
            order_by (Optional[str]): An ORDER BY clause, e.g., "timestamp DESC".
            limit (Optional[int]): Limits the number of records returned.
            offset (Optional[int]): The offset for the query.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the query results.
        """
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        table_name: str,
        data: Dict[str, Any],
        where: Tuple[str, Sequence[Any]],
    ) -> int:
        """
        Updates records in a table.

        Args:
            table_name (str): The name of the table.
            data (Dict[str, Any]): The columns and values to update.
            where (Tuple[str, Sequence[Any]]): A WHERE clause to identify the rows to update.

        Returns:
            int: The number of successfully updated records.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, table_name: str, where: Tuple[str, Sequence[Any]]) -> int:
        """
        Deletes records from a table.

        Args:
            table_name (str): The name of the table.
            where (Tuple[str, Sequence[Any]]): A WHERE clause to identify the rows to delete.

        Returns:
            int: The number of successfully deleted records.
        """
        raise NotImplementedError

    @abstractmethod
    async def execute_raw_sql(self, query: str, *params: Any) -> Any:
        """
        Executes a raw SQL command that does not return a dataset (e.g., DDL, DML).

        Args:
            query (str): The SQL statement to execute.
            *params: Parameters for the SQL statement.

        Returns:
            Any: The execution result, typically a status string or the number of affected rows, depending on the driver.
        """
        raise NotImplementedError

    @abstractmethod
    async def fetch_raw_sql(self, query: str, *params: Any) -> List[Dict[str, Any]]:
        """
        Executes a raw SQL query that returns a dataset (e.g., SELECT).

        Args:
            query (str): The SQL query to execute.
            *params: Parameters for the SQL query.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the query results.
        """
        raise NotImplementedError
