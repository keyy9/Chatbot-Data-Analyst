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
- You will be provided with a "RECENT CONVERSATION HISTORY" block. Use this history to resolve pronouns (e.g. "it", "them", "those", "their"), implicit entities, active filters, and follow-up requests.
- Maintain context naturally throughout the conversation. Do not treat every message as a completely new request.
- **STATEFUL FILTER RETENTION**: When the user asks a follow-up question (e.g. "who bought those?", "what about in Jakarta?", "show top 5 of those"), PRESERVE the existing active WHERE filter conditions (e.g., date ranges, product categories, status filters, or price thresholds) from previous queries in the conversation history, unless the user explicitly requests to change or clear them.
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

## ANSWER SHAPE (these decide whether the answer is usable):

1. **Always return the measure next to the label.** For "which/what X has the most/least/highest/lowest Y",
   select BOTH the identifying column AND the number that ranks it. `SELECT category` answers "which",
   but the reader cannot see *how many*, so the answer is incomplete.
   - Wrong: `SELECT category FROM products GROUP BY category ORDER BY COUNT(*) DESC LIMIT 1`
   - Right: `SELECT category, COUNT(*) AS product_count FROM products GROUP BY category ORDER BY product_count DESC LIMIT 1`

2. **Round averages and money.** Wrap AVG in ROUND - `ROUND(AVG(x), 2)` for prices and rates,
   `ROUND(AVG(x))` for whole currency amounts. A raw `AVG` returns a value like 301477.611940298507,
   which is noise, not an answer.

3. **Always ORDER BY when you GROUP BY.** A grouped result without ORDER BY comes back in an arbitrary
   order. Order by the measure (DESC) when the question is about ranking, or by the label when the
   question asks for a plain breakdown ("per tier", "in each city").

4. **Map status words in the question to status filters.** These are real column values, not adjectives:
   - "paid" / "paid payments" → `payments.status = 'paid'`
   - "completed" / "completed orders" → `orders.status = 'completed'`
   - "refunded" / "cancelled" → the matching `status` value
   Omitting the filter silently answers a different question than the one asked.

5. **Never select a column from a table you did not join.** Category lives on `products`, so revenue per
   category has to reach `products` through `order_items` - `order_items` alone has no category.

6. **String comparisons are case-sensitive in PostgreSQL.** `city = 'jakarta'` matches nothing when the
   stored value is `'Jakarta'`. Copy the exact casing from the schema's "Example values" list. That list
   is a sample, so a value you need may be missing from it - when it is, keep the casing the user wrote
   (place and person names are capitalised).

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
    # Every example below is a runnable query against THIS database. They exist
    # to demonstrate the four things generated SQL most often gets wrong:
    # label+measure projection, ROUND on averages, status filters, and reaching
    # a column through the right join. An example that references a column the
    # schema doesn't have teaches the model to invent columns, so keep these in
    # sync with the schema whenever it changes.
    EXAMPLES = [
        {
            "user_question": "Which category has the most products?",
            "sql": "SELECT category, COUNT(*) AS product_count FROM products GROUP BY category ORDER BY product_count DESC LIMIT 1;",
            "explanation": "Ranking: return the label AND the measure that ranks it"
        },
        {
            "user_question": "Which 5 product categories generated the most revenue from completed orders?",
            "sql": "SELECT p.category, SUM(oi.line_total) AS total_revenue FROM order_items oi INNER JOIN orders o ON oi.order_id = o.order_id INNER JOIN products p ON oi.product_id = p.product_id WHERE o.status = 'completed' GROUP BY p.category ORDER BY total_revenue DESC LIMIT 5;",
            "explanation": "Category lives on products, so revenue reaches it through order_items"
        },
        {
            "user_question": "What is the average order total for completed orders?",
            "sql": "SELECT ROUND(AVG(order_total)) AS average_order_total FROM orders WHERE status = 'completed';",
            "explanation": "Average is rounded, and 'completed' becomes a status filter"
        },
        {
            "user_question": "What is the total amount paid via virtual account?",
            "sql": "SELECT SUM(amount) AS total_paid FROM payments WHERE method = 'virtual_account' AND status = 'paid';",
            "explanation": "Both the method and the 'paid' status must be filtered"
        },
        {
            "user_question": "How many customers are in each tier?",
            "sql": "SELECT tier, COUNT(*) AS customer_count FROM customers GROUP BY tier ORDER BY tier;",
            "explanation": "A plain breakdown is ordered by the label so the output is stable"
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

    def build_user_prompt(
        self,
        user_question: str,
        conversation_context: str = "",
        allow_writes: bool = False
    ) -> str:
        """
        Build the user prompt for a specific question.

        Args:
            user_question: The user's natural language question.
            conversation_context: Prior turns, when this is a follow-up.
            allow_writes: True on the admin path, where INSERT/UPDATE/DELETE
                are permitted.

        Returns:
            str: Formatted user prompt ready for LLM.

        Note:
            The closing line is the last thing the model reads, so it carries
            more weight than anything earlier. It used to say "Return only the
            PostgreSQL SELECT query" unconditionally - including for admin write
            requests, whose system prompt says the opposite. The model followed
            the closing line, so "delete the customer named X" came back as a
            SELECT: no error, no confirmation prompt, nothing deleted.
        """
        context = f"\n\n{conversation_context}" if conversation_context else ""

        closing = (
            "Return only the PostgreSQL statement. If the request asks to change, "
            "add, or remove data, return an INSERT, UPDATE or DELETE - never a SELECT."
            if allow_writes
            else "Return only the PostgreSQL SELECT query."
        )

        return (
            "Current user request (this is the request you must answer):\n"
            f"{user_question}{context}\n\n{closing}"
        )

    def build_complete_prompt(
        self,
        user_question: str,
        schema_definition: str,
        include_examples: bool = False,
        num_examples: int = 3,
        override_system_prompt: Optional[str] = None,
        conversation_context: str = "",
        allow_writes: bool = False
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
        
        user_prompt = self.build_user_prompt(user_question, conversation_context, allow_writes)
        
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
