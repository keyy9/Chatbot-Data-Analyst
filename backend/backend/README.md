# AI/LLM Core Module - Conversational Data Analyst

Production-quality Python implementation of an AI-powered conversational data analyst system.

## 🎯 Overview

This module enables users to ask natural language questions about their database and automatically:
1. **Generate SQL** - Convert natural language to PostgreSQL
2. **Validate Safety** - Ensure queries are safe and read-only
3. **Execute Queries** - Run through backend database
4. **Explain Results** - Convert data to natural language
5. **Recommend Charts** - Suggest appropriate visualizations

## 📦 Architecture

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create `.env` file:

```env
# Groq
GROQ_API_KEY=gsk-your-key-here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TEMPERATURE=0.3
GROQ_MAX_TOKENS=1024

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
DATABASE_SCHEMA=public

# Application
APP_ENV=development
APP_DEBUG=true
LOG_LEVEL=INFO

# Validation
ENABLE_SQL_VALIDATION=true
MAX_QUERY_TIMEOUT=30

# Features
ENABLE_CLARIFICATION=true
ENABLE_MONITORING=true
```

### 3. Basic Usage

```python
from backend.ai import (
    initialize_ai_core,
    get_pipeline_orchestrator
)
from backend.ai.utils.supabase_schema_loader import get_supabase_schema_loader

# Initialize
initialize_ai_core()

# Get components
orchestrator = get_pipeline_orchestrator()
schema_loader = get_supabase_schema_loader()

# Get schema
schema = schema_loader.get_schema_definition()

# Process user question
async def process_question(user_question):
    def execute_sql(sql):
        # Backend executes SQL and returns (data, columns, execution_time)
        # This is called by the orchestrator
        return backend.execute_sql(sql)
    
    result = orchestrator.process(
        user_question=user_question,
        schema_definition=schema,
        query_executor_callback=execute_sql
    )
    
    return result
```

## 📊 Module Documentation

### Config Module (`config.py`)

Centralized configuration management using Pydantic.

```python
from backend.ai.config import get_settings, is_production

settings = get_settings()
print(settings.groq_api_key)
print(is_production())  # False for development
```

### Prompt Managers

#### SQLPromptManager

```python
from backend.ai.prompts.sql_prompt import get_sql_prompt_manager

manager = get_sql_prompt_manager()

prompt = manager.build_complete_prompt(
    user_question="Show top 5 products by revenue",
    schema_definition=schema,
    include_examples=True,
    num_examples=3
)

# Returns {"system": "...", "user": "..."}
```

#### ClarificationPromptManager

```python
from backend.ai.prompts.clarification_prompt import get_clarification_prompt_manager

manager = get_clarification_prompt_manager()

# Detect ambiguity
result = manager.build_clarification_prompt("Show sales")
# Returns clarification question if ambiguous

# Merge clarification
clarified = manager.merge_clarification_with_question(
    "Show sales",
    "This month"
)
# Returns: "Show sales for This month"
```

#### ExplanationPromptManager

```python
from backend.ai.prompts.explanation_prompt import (
    get_explanation_prompt_manager,
    QueryResult,
    ResultType
)

manager = get_explanation_prompt_manager()

# Create query result
result = QueryResult(
    data=[{"product": "Widget", "sales": 1500}],
    row_count=1,
    columns=["product", "sales"],
    execution_time=125,
    result_type=ResultType.SINGLE_METRIC
)

# Generate simple explanation
simple = manager.generate_simple_explanation(
    "What's the top product?",
    result
)
```

#### ChartPromptManager

```python
from backend.ai.prompts.chart_prompt import get_chart_prompt_manager

manager = get_chart_prompt_manager()

recommendation = manager.recommend_chart(
    data=query_result,
    columns=["date", "revenue"],
    query_type="time_series"
)

print(recommendation.chart_type.value)  # "line"
print(recommendation.confidence_score)  # 0.92
```

### LLM Client (`llm/client.py`)

#### Synchronous Client

```python
from backend.ai.llm.client import get_llm_client, LLMClientConfig

# Get default client
client = get_llm_client()

# Or create with custom config
config = LLMClientConfig(
    api_key="sk-...",
    model="llama-3.1-8b-instant",
    temperature=0.3,
    max_tokens=1024
)
client = LLMClient(config)

# Generate response
response = client.generate(
    system_prompt="You are a SQL expert",
    user_prompt="Generate SQL for top 5 products"
)

print(response.content)
print(response.input_tokens)
print(response.estimated_cost)
```

#### Asynchronous Client

```python
from backend.ai.llm.client import get_async_llm_client

client = get_async_llm_client()

# Single call
response = await client.generate(
    system_prompt="...",
    user_prompt="..."
)

# Batch calls
prompts = [
    {"system": "...", "user": "..."},
    {"system": "...", "user": "..."}
]

responses = await client.generate_batch(
    prompts,
    max_concurrent=5
)
```

#### Token Counting & Cost

```python
from backend.ai.llm.client import TokenCounter

# Estimate tokens
tokens = TokenCounter.estimate_tokens("Your text here")

# Estimate prompt tokens
prompt_tokens = TokenCounter.estimate_prompt_tokens(
    system_prompt="...",
    user_prompt="..."
)

# Estimate cost
cost = TokenCounter.estimate_cost(
    model="llama-3.3-70b-versatile",
    input_tokens=100,
    output_tokens=50
)
print(f"Cost: ${cost:.4f}")
```

### Generators (`llm/generator.py`)

#### SQLGenerator

```python
from backend.ai.llm.generator import get_sql_generator

generator = get_sql_generator()

result = generator.generate(
    user_question="Show top products",
    schema_definition=schema
)

if result.is_ambiguous:
    print(result.clarification_question)
    print(result.clarification_options)
elif result.is_valid:
    print(result.sql)
else:
    print(result.error_message)
```

#### ExplanationGenerator

```python
from backend.ai.llm.generator import get_explanation_generator
from backend.ai.prompts.explanation_prompt import QueryResult

generator = get_explanation_generator()

result = QueryResult(
    data=query_data,
    row_count=len(query_data),
    columns=columns,
    execution_time=125
)

explanation = generator.generate(
    user_question="What's the top product?",
    generated_sql="SELECT ...",
    query_result=result
)

print(explanation.explanation)
```

#### ChartRecommender

```python
from backend.ai.llm.generator import get_chart_recommender

recommender = get_chart_recommender()

recommendation = recommender.recommend(
    data=query_data,
    columns=columns,
    user_question="Show revenue trend",
    generated_sql="SELECT ..."
)

print(recommendation.chart_type)
print(recommendation.configuration)
```

#### PipelineOrchestrator

```python
from backend.ai.llm.generator import get_pipeline_orchestrator

orchestrator = get_pipeline_orchestrator()

response = orchestrator.process(
    user_question="What are the top 5 products?",
    schema_definition=schema,
    query_executor_callback=execute_sql_function
)

# Response contains:
# - status: "success" | "error" | "clarification_needed"
# - generated_sql
# - explanation
# - chart_recommendation
# - data
# - columns
# - metadata (timestamps, latencies)
```

### SQL Guard Validator (`validators/sql_guard.py`)

```python
from backend.ai.validators.sql_guard import get_sql_guard_validator

validator = get_sql_guard_validator(strict_mode=True)

result = validator.validate("SELECT * FROM products WHERE id = 1")

print(result["is_valid"])  # True
print(result["error"])  # None if valid

# Invalid SQL
result = validator.validate("DROP TABLE users")
print(result["is_valid"])  # False
print(result["error"])  # "DROP statement detected: ..."

# Get validation rules
rules = validator.get_validation_rules()
```

### Monitoring & Logging (`monitoring/logger.py`)

```python
from backend.ai.monitoring.logger import (
    get_monitoring_logger,
    EventType,
    EventSeverity
)

logger = get_monitoring_logger()

# Log SQL generation
event = logger.log_sql_generation(
    user_id="user123",
    session_id="session456",
    user_question="Show top products",
    generated_sql="SELECT ...",
    is_valid=True,
    is_ambiguous=False,
    duration_ms=250
)

# Log LLM call
llm_event = logger.log_llm_call(
    user_id="user123",
    session_id="session456",
    model="llama-3.3-70b-versatile",
    prompt_type="sql",
    input_tokens=150,
    output_tokens=50,
    latency_ms=1200,
    temperature=0.3,
    max_tokens=1024,
    finish_reason="stop",
    estimated_cost=0.015,
    success=True
)

# Get metrics
metrics = logger.get_metrics_summary(
    user_id="user123",
    time_range_minutes=60
)

print(metrics["total_events"])
print(metrics["success_rate"])
print(metrics["total_cost_usd"])

# Export
logger.export_events_json("events.json")
logger.export_metrics_json("metrics.json")
```

### Model Evaluation (`evaluation/evaluator.py`)

```python
from backend.ai.evaluation.evaluator import get_model_evaluator

evaluator = get_model_evaluator()

result = evaluator.evaluate(
    user_question="Show top 5 products",
    generated_sql="SELECT ...",
    query_result=data,
    execution_success=True,
    execution_time_ms=125,
    latency_ms=1500,
    available_tables=["products", "orders"],
    available_columns={
        "products": ["id", "name", "price"],
        "orders": ["id", "product_id", "amount"]
    }
)

print(result.overall_accuracy)  # 0.92
print(result.issues)  # List of issues found
print(result.recommendations)  # Improvement suggestions

# Batch evaluation
test_cases = [...]
results, summary = evaluator.batch_evaluate(
    test_cases,
    available_tables=tables,
    available_columns=columns
)

print(summary["average_accuracy"])
```

### Explanation Builder (`explanation/explainer.py`)

```python
from backend.ai.explanation.explainer import get_explanation_builder

builder = get_explanation_builder()

# Comprehensive explanation
explanation = builder.build_comprehensive_explanation(
    user_question="What are the top products?",
    data=query_data,
    columns=columns,
    include_insights=True,
    include_summary=True,
    include_statistics=False
)

print(explanation["insights"])
print(explanation["summary"])

# Narrative explanation
narrative = builder.build_narrative_explanation(
    user_question="What's the total revenue?",
    data=query_data,
    columns=columns
)

print(narrative)  # Natural language explanation
```

## 🧪 Testing

```bash
# Run tests
pytest tests/

# Run SQL validation tests
python -m backend.ai.validators.sql_guard

# Run with coverage
pytest --cov=backend/ai tests/
```

### Example Test Case

```python
from backend.ai.validators.sql_guard import get_sql_guard_validator

def test_sql_validation():
    validator = get_sql_guard_validator()
    
    # Valid SQL
    result = validator.validate("SELECT * FROM products WHERE price > 100")
    assert result["is_valid"] == True
    
    # Invalid SQL (INSERT)
    result = validator.validate("INSERT INTO products VALUES (1, 'Widget')")
    assert result["is_valid"] == False
    assert "INSERT" in result["error"]
```

## 📈 Performance Considerations

### Token Estimation

```python
from backend.ai.llm.client import TokenCounter

# Rough estimates:
# 1 token ≈ 4 characters
# System prompt: ~150 tokens
# User prompt: ~50 tokens
# Response: ~200 tokens
# Total: ~400 tokens ≈ $0.0003 (llama-3.3-70b-versatile)
```

### Caching Strategies

- **Schema caching**: Load once, reuse
- **Prompt caching**: Reuse system prompts
- **Result caching**: Cache query results by SQL hash

### Async Optimization

```python
from backend.ai.llm.client import get_async_llm_client

client = get_async_llm_client()

# Concurrent requests
responses = await client.generate_batch(
    prompts,
    max_concurrent=5  # Limit concurrent requests
)
```

## 🔐 Security Best Practices

1. **API Keys**: Store in environment variables, never in code
2. **SQL Validation**: Always validate before execution
3. **Rate Limiting**: Implement on API endpoints
4. **Monitoring**: Track all LLM API calls for audit
5. **Input Sanitization**: Validate all user inputs

## 🐛 Troubleshooting

### "GROQ_API_KEY not set"
- Ensure `.env` file exists
- Verify key is correct
- Run `python -c "from backend.ai.config import get_settings; print(get_settings().groq_api_key[:10])"`

### "SQL validation failed"
- Check forbidden keywords (INSERT, UPDATE, DELETE, etc.)
- Ensure balanced parentheses and quotes
- Review SQL Guard validation rules

### High Latency
- Check Groq API status
- Review token counts
- Consider using llama-3.1-8b-instant for faster responses

### High Costs
- Monitor token usage via monitoring logger
- Use simpler prompts where possible
- Cache results for repeated queries

## 📝 Contributing

1. Follow PEP8 style guide
2. Add docstrings to all functions
3. Write tests for new features
4. Update README with new functionality

## 📄 License

Proprietary - All Rights Reserved

## 👥 Support

For issues or questions, contact: ai-team@company.com