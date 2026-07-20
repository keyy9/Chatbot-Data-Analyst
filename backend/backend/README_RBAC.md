# Role-Based Access Control (RBAC) System

Supports 2 different interfaces:
- **USER Interface**: Read-only (SELECT only)
- **ADMIN Interface**: Full CRUD (SELECT, INSERT, UPDATE, DELETE)

## Roles

### USER (Read-Only)
- **Permissions**: READ only
- **Operations**: SELECT queries
- **Max Rows**: 1000 rows per query
- **Use Case**: End users asking questions about data

### ADMIN (Full Access)
- **Permissions**: READ, CREATE, UPDATE, DELETE
- **Operations**: SELECT, INSERT, UPDATE, DELETE
- **Max Rows**: Unlimited
- **Use Case**: Administrators managing data

### ANALYST (Advanced Read)
- **Permissions**: READ, EXPORT_DATA, VIEW_MONITORING
- **Operations**: SELECT queries + data export
- **Max Rows**: 10000 rows per query
- **Use Case**: Data analysts with export capabilities

### VIEWER (Limited Read)
- **Permissions**: READ only
- **Operations**: SELECT queries (very limited)
- **Max Rows**: 100 rows per query
- **Use Case**: Limited visibility access

## Usage Examples

### User Interface (Read-Only)

```python
from backend.ai.rbac.roles import Role
from backend.ai.rbac.access_control import UserContext

# Create user context
user_context = UserContext(
    user_id="user123",
    role=Role.USER,
    session_id="session456"
)

# Ask a question
from backend.api.routes.user_questions import ask_question

response = await ask_question({
    "question": "What are the top 5 products?",
    "user_id": "user123",
    "session_id": "session456"
})

# Result: SELECT query executed with 1000 row limit
```

### Admin Interface (Full CRUD)

```python
# Create new record
from backend.api.routes.admin_operations import create_record

response = await create_record({
    "table": "products",
    "data": {
        "product_name": "New Widget",
        "price": 99.99,
        "stock": 100
    },
    "user_id": "admin123",
    "session_id": "session789"
})

# Update record
from backend.api.routes.admin_operations import update_record

response = await update_record({
    "table": "products",
    "data": {"price": 109.99},
    "where_clause": "product_id = 5",
    "user_id": "admin123",
    "session_id": "session789"
})

# Delete record
from backend.api.routes.admin_operations import delete_record

response = await delete_record({
    "table": "products",
    "where_clause": "product_id = 5",
    "user_id": "admin123",
    "session_id": "session789"
})

# Custom SQL
from backend.api.routes.admin_operations import execute_custom_query

response = await execute_custom_query({
    "sql": "SELECT * FROM products WHERE stock > 50",
    "user_id": "admin123",
    "session_id": "session789"
})
```

## API Endpoints

### User Interface (Read-Only)