"""
Supabase Query Executor.

Executes validated SQL queries against Supabase database.
"""

import logging
from typing import Optional, Tuple, List, Dict, Any
import asyncio

from backend.ai.utils.supabase_client import SupabaseClient

# ============ Setup Logging ============
logger = logging.getLogger(__name__)


class SupabaseQueryExecutor:
    """
    Executes SQL queries against Supabase.
    
    Features:
    - Execute validated SELECT queries
    - Return formatted results
    - Handle errors gracefully
    - Support async execution
    """
    
    def __init__(self, supabase_client: SupabaseClient):
        """
        Initialize query executor.
        
        Args:
            supabase_client: SupabaseClient instance.
        """
        self.client = supabase_client
        logger.info("SupabaseQueryExecutor initialized")
    
    def execute(self, sql: str) -> Tuple[List[Dict], List[str], float]:
        """
        Execute a validated SQL query.
        
        Args:
            sql: The SQL query to execute.
        
        Returns:
            Tuple[List[Dict], List[str], float]:
                - Results (list of dicts)
                - Column names (list of strings)
                - Execution time in milliseconds
                
        Raises:
            Exception: If query execution fails.
            
        Example:
            results, columns, exec_time = executor.execute(
            "SELECT * FROM products WHERE stock > 10"
        )
        """
        try:
            logger.info(f"Executing query: {sql[:80]}...")
            
            data, row_count, execution_time = self.client.execute_query(sql)
            
            # Extract column names from first row
            columns = list(data[0].keys()) if data else []
            
            logger.info(
                f"Query executed successfully: "
                f"{row_count} rows, {len(columns)} columns, "
                f"{execution_time:.0f}ms"
            )
            
            return data, columns, execution_time
        
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise
    
    async def execute_async(self, sql: str) -> Tuple[List[Dict], List[str], float]:
        """
        Execute a query asynchronously.
        
        Args:
            sql: The SQL query to execute.
        
        Returns:
            Tuple: (results, columns, execution_time)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.execute, sql)
    
    def execute_with_limit(
        self,
        sql: str,
        max_rows: int = 1000
    ) -> Tuple[List[Dict], List[str], float]:
        """
        Execute query with row limit.
        
        Args:
            sql: The SQL query.
            max_rows: Maximum rows to return.
        
        Returns:
            Tuple: (results, columns, execution_time)
        """
        # Add LIMIT clause if not present. Strip a trailing semicolon first -
        # otherwise "SELECT ...;" becomes "SELECT ...; LIMIT n", which is a
        # syntax error (the semicolon already terminated the statement).
        sql = sql.strip()
        has_trailing_semicolon = sql.endswith(";")
        sql_body = sql[:-1] if has_trailing_semicolon else sql

        if "LIMIT" not in sql_body.upper():
            sql_body = f"{sql_body} LIMIT {max_rows}"

        return self.execute(sql_body)
    
    def execute_and_format(
        self,
        sql: str,
        format_type: str = "list"  # "list", "json", "csv"
    ) -> str:
        """
        Execute query and format results.
        
        Args:
            sql: The SQL query.
            format_type: Output format.
        
        Returns:
            str: Formatted results.
        """
        data, columns, _ = self.execute(sql)
        
        if format_type == "json":
            import json
            return json.dumps(data, indent=2, default=str)
        
        elif format_type == "csv":
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=columns)
            writer.writeheader()
            writer.writerows(data)
            
            return output.getvalue()
        
        else:  # list
            return str(data)


# ============ Singleton Instance ============
_supabase_executor: Optional[SupabaseQueryExecutor] = None


def get_supabase_query_executor(
    supabase_client: Optional[SupabaseClient] = None
) -> SupabaseQueryExecutor:
    """
    Get or create the global Supabase query executor instance.
    
    Args:
        supabase_client: SupabaseClient instance.
    
    Returns:
        SupabaseQueryExecutor: The executor instance.
    """
    global _supabase_executor
    
    if _supabase_executor is None:
        if supabase_client is None:
            from backend.ai.utils.supabase_client import get_supabase_client
            supabase_client = get_supabase_client()

        _supabase_executor = SupabaseQueryExecutor(supabase_client)
    
    return _supabase_executor