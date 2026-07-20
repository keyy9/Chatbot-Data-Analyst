"""
SQL Generation Prompt Module.

Manages all prompts related to SQL generation from natural language.
Handles dynamic schema injection, guardrail rules, and prompt engineering.
"""

from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SQLPromptTemplate:
    """
    Encapsulates SQL generation prompt with dynamic schema injection.
    
    Attributes:
        system_prompt: Core system instructions for the LLM
        user_context: Context about the database structure
        examples: Few-shot examples for better generation
    """
    
    system_prompt: str
    user_context: str
    examples: List[str]


class SQLPromptManager:
    """
    Manages SQL generation prompts and schema injection.
    
    Responsible for:
    - Building system prompts
    - Injecting database schema dynamically
    - Providing few-shot examples
    - Managing prompt versioning
    """
    
    # ============ SQL Generation System Prompt ============
    SYSTEM_PROMPT = """You are an expert PostgreSQL analyst that translates a user's request into one safe SQL query.

Your ONLY task is to convert natural language questions into valid PostgreSQL SQL queries.

## STRICT RULES:

1. **Output Format**: Return ONLY the SQL query. No markdown. No explanation. No backticks.
2. **Query Type**: ONLY SELECT queries are allowed. NEVER generate INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE, or MERGE statements.
3. **Data Safety**: You must NEVER modify, create, or delete any data.
4. **Schema Compliance**: Use ONLY the provided tables, columns, and relationships. NEVER invent a column, a status value, or a join condition.
5. **SQL Syntax**: Generate valid PostgreSQL syntax only. Use lowercase for SQL keywords.
6. **Security**: NEVER include comments (-- or /* */). NEVER allow SQL injection patterns.
7. **Single Query**: Return only ONE complete SQL statement. NEVER chain multiple statements with semicolons or CTEs that modify data.
8. **No Explanations**: Do NOT explain the query. Do NOT add any text before or after the SQL.
9. **Monetary Values**: All monetary values in the database are stored as raw numbers in IDR (Indonesian Rupiah). Do not divide, scale, or perform currency conversions unless explicitly requested.

## CONVERSATION MEMORY & MULTI-TURN CONTEXT:
- You will be provided with a "RECENT CONVERSATION HISTORY" block. Use this history to resolve pronouns (e.g. "it", "them", "those", "their"), implicit entities, and follow-up requests.
- Maintain context naturally throughout the conversation. Do not treat every message as a completely new request.
- If the user asks for a refinement (e.g. "only completed ones", "filter by electronics", "show their names"), modify the previous SQL query by appending or modifying its clauses rather than writing a completely new query from scratch.
- Do not carry over previous filters if the user starts a completely new topic or asks an unrelated question.

## BEST PRACTICES:

- Read the schema carefully before choosing a table or join. When a requested field lives in another table, join through the actual key shown in the schema.
- Use INNER JOIN for required relationships (LEFT JOIN only when missing related records must remain visible)
- Use WHERE clauses for filtering
- Use GROUP BY for aggregations
- Use ORDER BY DESC for ranking
- Use LIMIT for result limiting
- Handle date filtering properly (use CURRENT_DATE, CURRENT_TIMESTAMP)
- Use aggregate functions: COUNT(), SUM(), AVG(), MAX(), MIN()
- Use clear output aliases (for example `total_revenue`, `order_count`) and avoid returning internal IDs unless the user asks for them
- Do not silently add a date filter or a LIMIT that the user did not request. Ask for clarification upstream when the period matters.
- Use CASE statements for conditional logic

## COMMON PATTERNS:

### Time-based queries:
- "Today" → WHERE DATE(column) = CURRENT_DATE
- "This month" → WHERE EXTRACT(MONTH FROM column) = EXTRACT(MONTH FROM CURRENT_DATE) AND EXTRACT(YEAR FROM column) = EXTRACT(YEAR FROM CURRENT_DATE)
- "Last 7 days" → WHERE column >= CURRENT_DATE - INTERVAL '7 days'

### Aggregations:
- "Count" → SELECT COUNT(*)
- "Total" → SELECT SUM(column)
- "Average" → SELECT AVG(column)
- "Top N" → ORDER BY column DESC LIMIT N

### Filtering:
- "Like" patterns → ILIKE for case-insensitive matching
- "Between" → WHERE column BETWEEN value1 AND value2
- "In list" → WHERE column IN (value1, value2, value3)

Remember: Your ONLY output must be the SQL query. Nothing else."""

    # ============ Schema Injection Template ============
    SCHEMA_CONTEXT_TEMPLATE = """## DATABASE SCHEMA:

The available tables and columns are:

{schema_definition}

### Important Notes:
- All timestamps are in UTC
- Monetary values are in decimal format
- Dates are in YYYY-MM-DD format
- Use schema.table notation where necessary"""

    # ============ Few-Shot Examples ============
    EXAMPLES = [
        {
            "user_question": "Show products with stock below 20",
            "sql": "SELECT product_id, product_name, stock_quantity FROM products WHERE stock_quantity < 20 ORDER BY stock_quantity ASC;",
            "explanation": "Simple WHERE clause filtering"
        },
        {
            "user_question": "Total sales this month",
            "sql": "SELECT SUM(amount) as total_sales FROM orders WHERE EXTRACT(MONTH FROM order_date) = EXTRACT(MONTH FROM CURRENT_DATE) AND EXTRACT(YEAR FROM order_date) = EXTRACT(YEAR FROM CURRENT_DATE);",
            "explanation": "Aggregation with date filtering"
        },
        {
            "user_question": "Who is the top customer",
            "sql": "SELECT customer_id, customer_name, SUM(amount) as total_spent FROM orders GROUP BY customer_id, customer_name ORDER BY total_spent DESC LIMIT 1;",
            "explanation": "GROUP BY with aggregation and LIMIT"
        },
        {
            "user_question": "Revenue by category",
            "sql": "SELECT p.category, SUM(o.amount) as revenue FROM orders o INNER JOIN products p ON o.product_id = p.product_id GROUP BY p.category ORDER BY revenue DESC;",
            "explanation": "JOIN with GROUP BY aggregation"
        },
        {
            "user_question": "Compare sales between January and February",
            "sql": "SELECT EXTRACT(MONTH FROM order_date) as month, SUM(amount) as total_sales FROM orders WHERE EXTRACT(MONTH FROM order_date) IN (1, 2) AND EXTRACT(YEAR FROM order_date) = EXTRACT(YEAR FROM CURRENT_DATE) GROUP BY EXTRACT(MONTH FROM order_date) ORDER BY month;",
            "explanation": "Date filtering with GROUP BY for comparison"
        }
    ]

    def __init__(self):
        """Initialize the SQL Prompt Manager."""
        pass

    def build_system_prompt(self) -> str:
        """
        Get the system prompt for SQL generation.
        
        Returns:
            str: Complete system prompt with rules and guidelines.
        """
        return self.SYSTEM_PROMPT

    def build_schema_context(self, schema_definition: str) -> str:
        """
        Build schema context for injection into prompt.
        
        Args:
            schema_definition (str): The database schema definition (tables, columns, types).
            
        Returns:
            str: Formatted schema context ready for prompt injection.
            
        Example:
            schema = '''
        Table: products
          - product_id (INTEGER, PRIMARY KEY)
          - product_name (VARCHAR)
          - stock_quantity (INTEGER)
          - price (DECIMAL)
        '''
        context = manager.build_schema_context(schema)
        """
        return self.SCHEMA_CONTEXT_TEMPLATE.format(schema_definition=schema_definition)

    def build_few_shot_examples(self, num_examples: int = 3) -> str:
        """
        Build few-shot examples for in-context learning.
        
        Args:
            num_examples (int): Number of examples to include (default: 3, max: 5).
            
        Returns:
            str: Formatted examples for the prompt.
        """
        num_examples = min(num_examples, len(self.EXAMPLES))
        
        examples_text = "## EXAMPLES:\n\n"
        for i, example in enumerate(self.EXAMPLES[:num_examples], 1):
            examples_text += f"""Example {i}:
User: {example['user_question']}
SQL: {example['sql']}

"""
        
        return examples_text

    def build_user_prompt(self, user_question: str, conversation_context: str = "") -> str:
        """
        Build the user prompt for a specific question.
        
        Args:
            user_question (str): The user's natural language question.
            
        Returns:
            str: Formatted user prompt ready for LLM.
        """
        context = f"\n\n{conversation_context}" if conversation_context else ""
        return (
            "Current user request (this is the request you must answer):\n"
            f"{user_question}{context}\n\nReturn only the PostgreSQL SELECT query."
        )

    def build_complete_prompt(
        self,
        user_question: str,
        schema_definition: str,
        include_examples: bool = False,
        num_examples: int = 3,
        override_system_prompt: Optional[str] = None,
        conversation_context: str = ""
    ) -> Dict[str, str]:
        """
        Build a complete prompt with all components.

        This is the main method to call when generating SQL.

        Args:
            user_question (str): The natural language question.
            schema_definition (str): The database schema.
            include_examples (bool): Whether to include few-shot examples.
            num_examples (int): Number of examples if included.
            override_system_prompt (Optional[str]): If provided (e.g. an
                admin-editable prompt loaded from the database), used in
                place of the hardcoded SYSTEM_PROMPT. The schema context
                is always freshly injected regardless, since it must stay
                in sync with the live database.

        Returns:
            Dict[str, str]: Dictionary with 'system' and 'user' keys for API call.

        Example:
            prompt = manager.build_complete_prompt(
            user_question="Show top 5 products",
            schema_definition=schema,
            include_examples=True,
            num_examples=3
        )
        # Returns: {"system": "...", "user": "..."}
        """
        system_prompt = override_system_prompt or self.build_system_prompt()
        schema_context = self.build_schema_context(schema_definition)
        
        # Combine system prompt and schema
        full_system = f"{system_prompt}\n\n{schema_context}"
        
        # Add examples if requested
        if include_examples:
            examples = self.build_few_shot_examples(num_examples)
            full_system = f"{full_system}\n\n{examples}"
        
        user_prompt = self.build_user_prompt(user_question, conversation_context)
        
        return {
            "system": full_system,
            "user": user_prompt
        }

    def validate_prompt_structure(self, prompt_dict: Dict[str, str]) -> bool:
        """
        Validate the structure of a generated prompt.
        
        Args:
            prompt_dict (Dict[str, str]): The prompt dictionary to validate.
            
        Returns:
            bool: True if prompt structure is valid.
            
        Raises:
            ValueError: If prompt structure is invalid.
        """
        if not isinstance(prompt_dict, dict):
            raise ValueError("Prompt must be a dictionary")
        
        if "system" not in prompt_dict or "user" not in prompt_dict:
            raise ValueError("Prompt must have 'system' and 'user' keys")
        
        if not isinstance(prompt_dict["system"], str) or len(prompt_dict["system"]) == 0:
            raise ValueError("System prompt must be non-empty string")
        
        if not isinstance(prompt_dict["user"], str) or len(prompt_dict["user"]) == 0:
            raise ValueError("User prompt must be non-empty string")
        
        return True


# ============ Schema Definition Helper ============
class SchemaFormatter:
    """
    Utility class for formatting database schema for prompt injection.
    """
    
    @staticmethod
    def format_table_schema(
        table_name: str,
        columns: List[Dict[str, str]]
    ) -> str:
        """
        Format a single table schema.
        
        Args:
            table_name (str): Name of the table.
            columns (List[Dict[str, str]]): List of column definitions.
                Each dict should have: {'name': str, 'type': str, 'description': str (optional)}
        
        Returns:
            str: Formatted schema string.
            
        Example:
            schema = SchemaFormatter.format_table_schema(
            "products",
            [
                {"name": "product_id", "type": "INTEGER", "description": "Primary key"},
                {"name": "product_name", "type": "VARCHAR(255)"},
            ]
        )
        """
        schema_text = f"Table: {table_name}\n"
        for col in columns:
            col_name = col.get("name", "")
            col_type = col.get("type", "")
            col_desc = col.get("description", "")
            
            if col_desc:
                schema_text += f"  - {col_name} ({col_type}) - {col_desc}\n"
            else:
                schema_text += f"  - {col_name} ({col_type})\n"
        
        return schema_text

    @staticmethod
    def format_complete_schema(tables: List[Dict]) -> str:
        """
        Format a complete database schema.
        
        Args:
            tables (List[Dict]): List of table definitions.
                Each dict should have: {'name': str, 'columns': List[Dict]}
        
        Returns:
            str: Formatted complete schema.
        """
        schema_text = ""
        for table in tables:
            table_name = table.get("name", "")
            columns = table.get("columns", [])
            
            schema_text += SchemaFormatter.format_table_schema(table_name, columns)
            schema_text += "\n"
        
        return schema_text.strip()


# ============ Singleton Instance ============
sql_prompt_manager = SQLPromptManager()


def get_sql_prompt_manager() -> SQLPromptManager:
    """
    Get the global SQL Prompt Manager instance.
    
    Returns:
        SQLPromptManager: The prompt manager instance.
    """
    return sql_prompt_manager
