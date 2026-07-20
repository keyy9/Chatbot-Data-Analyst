"""
Complete example using Supabase integration.

Reads connection details from environment variables - never hardcode
credentials here. Copy `.env.example` (or your own `.env`) with
DATABASE_URL set before running these examples.
"""

import os

from backend.ai import initialize_ai_core, get_sql_generator, get_chart_recommender
from backend.ai.utils.supabase_client import SupabaseClient, SupabaseConfig
from backend.ai.utils.supabase_schema_loader import get_supabase_schema_loader
from backend.ai.utils.supabase_executor import get_supabase_query_executor


def _config_from_env() -> SupabaseConfig:
    """Build a SupabaseConfig from environment variables."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Set DATABASE_URL in your environment/.env before running this example.")

    return SupabaseConfig(
        database_url=database_url,
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_key=os.getenv("SUPABASE_KEY", ""),
        schema=os.getenv("DATABASE_SCHEMA", "public")
    )


def example_basic_usage():
    """Basic usage example with Supabase."""

    # ============ Step 1: Configure Supabase ============
    supabase_config = _config_from_env()

    # ============ Step 2: Initialize AI Core ============
    initialize_ai_core()

    # ============ Step 3: Get Schema from Supabase ============
    supabase_client = SupabaseClient(supabase_config)

    # Test connection
    if not supabase_client.test_connection():
        print("Failed to connect to Supabase!")
        return

    print("✓ Connected to Supabase")

    # Get schema
    schema_loader = get_supabase_schema_loader(supabase_client)
    schema_definition = schema_loader.get_schema_definition()

    print("\n=== DATABASE SCHEMA ===")
    print(schema_definition)

    # ============ Step 4: Setup Query Executor ============
    query_executor = get_supabase_query_executor(supabase_client)

    # ============ Step 5: Process User Questions ============
    sql_generator = get_sql_generator()
    chart_recommender = get_chart_recommender()

    user_questions = [
        "Show the top 5 products by sales",
        "How many customers do we have?",
        "What's the total revenue this month?"
    ]

    for question in user_questions:
        print(f"\n{'='*60}")
        print(f"Question: {question}")
        print('='*60)

        # 1) Generate SQL
        sql_result = sql_generator.generate(
            user_question=question,
            schema_definition=schema_definition
        )

        if sql_result.is_ambiguous:
            print(f"\n? Clarification needed: {sql_result.clarification_question}")
            print(f"  Options: {sql_result.clarification_options}")
            continue

        if not sql_result.is_valid:
            print(f"\n✗ SQL generation failed: {sql_result.error_message}")
            continue

        generated_sql = sql_result.sql
        print(f"\n✓ SQL Generated:")
        print(f"  {generated_sql[:100]}...")

        # 2) Execute SQL
        results, columns, exec_time = query_executor.execute(generated_sql)

        print(f"\n✓ Data (first 3 rows):")
        for row in results[:3]:
            print(f"  {row}")
        print(f"  Columns: {columns}")
        print(f"  Execution time: {exec_time:.0f}ms")

        # 3) Recommend chart (rule-based by default)
        chart_result = chart_recommender.recommend(
            data=results,
            columns=columns,
            user_question=question,
            generated_sql=generated_sql
        )

        print(f"\n✓ Chart recommendation: {chart_result.chart_type} ({chart_result.reason})")


def example_direct_query_execution():
    """Direct query execution example."""

    supabase_client = SupabaseClient(_config_from_env())
    executor = get_supabase_query_executor(supabase_client)

    # Execute a validated SQL query
    sql = "SELECT * FROM products WHERE price > 100 LIMIT 10"

    try:
        results, columns, execution_time = executor.execute(sql)

        print(f"Columns: {columns}")
        print(f"Rows: {len(results)}")
        print(f"Execution time: {execution_time:.0f}ms")

        for row in results:
            print(row)

    except Exception as e:
        print(f"Error: {e}")


def example_schema_inspection():
    """Schema inspection example."""

    supabase_client = SupabaseClient(_config_from_env())
    schema_loader = get_supabase_schema_loader(supabase_client)

    # Get all tables
    print("Tables in schema:")
    for table in schema_loader.get_available_tables():
        print(f"  - {table}")

    # Get table info
    print("\nTable details:")
    table_info = schema_loader.get_table_info("products")
    print(f"  Table: {table_info['name']}")
    print(f"  Columns: {table_info['column_count']}")

    for col in table_info['columns'][:3]:
        print(f"    - {col['name']} ({col['type']})")

    # Get sample data
    print("\nSample data:")
    samples = schema_loader.get_sample_data("products", limit=3)
    for sample in samples:
        print(f"  {sample}")


async def example_async_execution():
    """Async query execution example."""
    import asyncio

    supabase_client = SupabaseClient(_config_from_env())
    executor = get_supabase_query_executor(supabase_client)

    # Execute multiple queries in parallel
    queries = [
        "SELECT COUNT(*) as product_count FROM products",
        "SELECT COUNT(*) as order_count FROM orders",
        "SELECT COUNT(*) as customer_count FROM customers"
    ]

    tasks = [executor.execute_async(sql) for sql in queries]
    results = await asyncio.gather(*tasks)

    for sql, (data, cols, time) in zip(queries, results):
        print(f"{sql[:40]}: {data[0]} in {time:.0f}ms")


if __name__ == "__main__":
    # Run examples
    print("=" * 80)
    print("SUPABASE INTEGRATION EXAMPLES")
    print("=" * 80)

    # Uncomment to run:
    # example_basic_usage()
    # example_direct_query_execution()
    # example_schema_inspection()
    # asyncio.run(example_async_execution())

    print("\nExamples completed!")
