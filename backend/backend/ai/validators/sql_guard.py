"""
SQL Guard Validator Module.

Validates generated SQL queries to ensure safety and prevent dangerous operations.
Only allows SELECT queries, blocks all DML/DDL operations.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# ============ Setup Logging ============
logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """
    Represents a SQL validation error.
    
    Attributes:
        error_type: Type of validation error
        message: Detailed error message
        severity: Severity level (info, warning, critical)
        location: Location in SQL where error was found (optional)
    """
    error_type: str
    message: str
    severity: str = "critical"
    location: Optional[str] = None
    
    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.error_type}: {self.message}"


class SQLGuardValidator:
    """
    Validates SQL queries to ensure they are safe and secure.
    
    Security Rules Enforced:
    1. Only SELECT queries allowed (no INSERT, UPDATE, DELETE, etc.)
    2. No data modification operations
    3. No SQL injection attempts
    4. No multiple SQL statements
    5. No comments
    6. No DROP, ALTER, CREATE operations
    7. No schema modification
    
    This is a defensive validator that takes a restrictive approach.
    When in doubt, it rejects the query.
    """
    
    # ============ Forbidden SQL Statements ============
    FORBIDDEN_STATEMENTS = {
        "INSERT": "Data insertion not allowed",
        "UPDATE": "Data modification not allowed",
        "DELETE": "Data deletion not allowed",
        "DROP": "Table/schema deletion not allowed",
        "ALTER": "Schema modification not allowed",
        "TRUNCATE": "Table truncation not allowed",
        "CREATE": "Table/schema creation not allowed",
        "GRANT": "Permission modification not allowed",
        "REVOKE": "Permission revocation not allowed",
        "MERGE": "Merge operations not allowed",
        "EXEC": "Dynamic SQL execution not allowed",
        "EXECUTE": "Procedure execution not allowed",
        "PRAGMA": "Pragma commands not allowed",
        "VACUUM": "Vacuum operations not allowed",
        "EXPLAIN": "Query plans not allowed",
        "ANALYZE": "Table analysis not allowed"
    }
    
    # ============ SQL Injection Patterns ============
    # Note: OR/AND tautology checks below intentionally require both sides of
    # the "=" to be identical (e.g. "OR 1=1", "OR ''=''") rather than matching
    # any OR/AND followed by any "=" - the broader form flags completely
    # ordinary filters like "AND category = 'electronics'" as malicious.
    SQL_INJECTION_PATTERNS = [
        r"\b(?:OR|AND)\b\s+(\d+)\s*=\s*\1\b",  # OR 1=1 / AND 1=1
        r"\b(?:OR|AND)\b\s+'([^']*)'\s*=\s*'\1'",  # OR ''='' / OR 'x'='x'
        r"(;.*\w+)",  # Statement separator
        r"(/\*.*\*/)",  # Multi-line comments
        r"(--.*)",  # Single-line comments
        r"(\bUNION\b.*\bSELECT\b)",  # UNION-based injection
        r"(xp_cmdshell)",  # Command execution
        r"(sp_executesql)",  # Dynamic execution
        r"(0x[0-9a-f]+)",  # Hex encoding for bypassing quotes
        r"(char\()",  # Char function for encoding
        r"(\bWAITFOR\b)",  # Time-based blind SQLi
        r"(BENCHMARK|SLEEP)\(",  # Timing functions
        r"(\bINTO\b.*\bOUTFILE\b)",  # File write
        r"(\bINTO\b.*\bDUMPFILE\b)",  # File write
    ]
    
    # ============ Dangerous Pattern Keywords ============
    DANGEROUS_KEYWORDS = [
        "EXEC",
        "EXECUTE",
        "SCRIPT",
        "EVAL",
        "SYSTEM",
        "SHELL",
        "CMD",
        "COMMAND"
    ]
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize SQL Guard Validator.
        
        Args:
            strict_mode: If True, be very strict with validation.
                        If False, allow some edge cases.
        """
        self.strict_mode = strict_mode
        logger.info(f"SQLGuardValidator initialized (strict_mode={strict_mode})")
    
    def validate(self, sql_query: str) -> Dict:
        """
        Validate a SQL query.
        
        Main validation method. Returns detailed validation result.
        
        Args:
            sql_query: The SQL query to validate.
        
        Returns:
            Dict: Validation result with keys:
                {
                    "is_valid": bool,
                    "error": str (only if invalid),
                    "error_type": str (only if invalid),
                    "warnings": List[str],
                    "checks_passed": List[str]
                }
                
        Example:
            validator = SQLGuardValidator()
        
        # Valid query
        result = validator.validate("SELECT * FROM products WHERE id = 1")
        assert result["is_valid"] == True
        
        # Invalid query
        result = validator.validate("DROP TABLE users")
        assert result["is_valid"] == False
        assert "DROP" in result["error"]
        """
        logger.info(f"Validating SQL: {sql_query[:100]}...")
        
        errors = []
        warnings = []
        checks_passed = []
        
        # Normalize SQL for analysis
        normalized_sql = self._normalize_sql(sql_query)
        
        # ============ Check 1: Basic Format ============
        if not sql_query or len(sql_query.strip()) == 0:
            errors.append(ValidationError(
                error_type="EMPTY_QUERY",
                message="SQL query is empty",
                severity="critical"
            ))
            return self._format_result(False, errors, warnings, checks_passed)
        
        if len(sql_query) > 10000:
            errors.append(ValidationError(
                error_type="QUERY_TOO_LONG",
                message="SQL query exceeds maximum length (10000 characters)",
                severity="critical"
            ))
            return self._format_result(False, errors, warnings, checks_passed)
        
        checks_passed.append("Basic format check passed")
        
        # ============ Check 2: Forbidden Statements ============
        forbidden_check = self._check_forbidden_statements(normalized_sql)
        if forbidden_check["has_forbidden"]:
            for error in forbidden_check["errors"]:
                errors.append(error)
        else:
            checks_passed.append("No forbidden SQL statements detected")
        
        # ============ Check 3: Comments ============
        comment_check = self._check_for_comments(sql_query)
        if comment_check["has_comments"]:
            errors.append(ValidationError(
                error_type="COMMENTS_DETECTED",
                message=f"SQL comments detected: {comment_check['comment_types']}. "
                        "Comments are not allowed for security reasons.",
                severity="critical"
            ))
        else:
            checks_passed.append("No comments detected")
        
        # ============ Check 4: Multiple Statements ============
        multi_stmt_check = self._check_multiple_statements(sql_query)
        if multi_stmt_check["has_multiple"]:
            errors.append(ValidationError(
                error_type="MULTIPLE_STATEMENTS",
                message="Multiple SQL statements detected. Only single statements are allowed.",
                severity="critical"
            ))
        else:
            checks_passed.append("Single statement validation passed")
        
        # ============ Check 5: SQL Injection Patterns ============
        injection_check = self._check_sql_injection_patterns(normalized_sql)
        if injection_check["suspicious_patterns"]:
            if self.strict_mode:
                for pattern in injection_check["suspicious_patterns"]:
                    errors.append(ValidationError(
                        error_type="SQL_INJECTION_DETECTED",
                        message=f"Suspicious pattern detected: {pattern}",
                        severity="critical"
                    ))
            else:
                warnings.append(f"Suspicious patterns detected: {injection_check['suspicious_patterns']}")
        else:
            checks_passed.append("No SQL injection patterns detected")
        
        # ============ Check 6: SELECT Statement Validation ============
        if normalized_sql.strip().upper().startswith("SELECT"):
            select_check = self._validate_select_statement(normalized_sql)
            
            if not select_check["is_valid"]:
                for error in select_check["errors"]:
                    errors.append(error)
            else:
                checks_passed.append("SELECT statement validation passed")
        else:
            errors.append(ValidationError(
                error_type="NOT_SELECT",
                message="Query must start with SELECT. Only read operations are allowed.",
                severity="critical"
            ))
        
        # ============ Check 7: Schema Validation ============
        schema_check = self._check_schema_operations(normalized_sql)
        if schema_check["has_schema_ops"]:
            for error in schema_check["errors"]:
                errors.append(error)
        else:
            checks_passed.append("No schema modification operations detected")
        
        # ============ Return Result ============
        is_valid = len(errors) == 0
        
        if is_valid:
            logger.info(f"SQL validation PASSED. Checks passed: {len(checks_passed)}")
        else:
            logger.warning(f"SQL validation FAILED. Errors: {len(errors)}")
        
        return self._format_result(is_valid, errors, warnings, checks_passed)
    
    def _normalize_sql(self, sql: str) -> str:
        """
        Normalize SQL for analysis.
        
        - Remove leading/trailing whitespace
        - Collapse multiple whitespaces
        - Convert to uppercase for keyword matching
        
        Args:
            sql: The SQL query.
        
        Returns:
            str: Normalized SQL.
        """
        # Remove leading/trailing whitespace
        sql = sql.strip()
        
        # Collapse multiple whitespaces
        sql = re.sub(r'\s+', ' ', sql)
        
        return sql
    
    def _check_forbidden_statements(self, normalized_sql: str) -> Dict:
        """
        Check for forbidden SQL statements.
        
        Args:
            normalized_sql: Normalized SQL query.
        
        Returns:
            Dict: Check result with forbidden statements found.
        """
        errors = []
        has_forbidden = False
        
        sql_upper = normalized_sql.upper()
        
        for keyword, description in self.FORBIDDEN_STATEMENTS.items():
            # Look for the keyword as a whole word (with word boundaries)
            pattern = r'\b' + keyword + r'\b'
            
            if re.search(pattern, sql_upper):
                has_forbidden = True
                errors.append(ValidationError(
                    error_type=f"FORBIDDEN_{keyword}",
                    message=f"{keyword} statement detected: {description}",
                    severity="critical"
                ))
                logger.warning(f"Forbidden statement detected: {keyword}")
        
        return {
            "has_forbidden": has_forbidden,
            "errors": errors
        }
    
    def _check_for_comments(self, sql: str) -> Dict:
        """
        Check for SQL comments.
        
        Args:
            sql: The SQL query.
        
        Returns:
            Dict: Check result with comment types found.
        """
        comment_types = []
        
        # Single-line comments (-- comment)
        if re.search(r'--\s*\S', sql):
            comment_types.append("single-line (--)")
        
        # Multi-line comments (/* comment */)
        if re.search(r'/\*.*?\*/', sql, re.DOTALL):
            comment_types.append("multi-line (/* */)")
        
        # MySQL comments (# comment)
        if re.search(r'#\s*\S', sql):
            comment_types.append("MySQL (#)")
        
        return {
            "has_comments": len(comment_types) > 0,
            "comment_types": comment_types
        }
    
    def _check_multiple_statements(self, sql: str) -> Dict:
        """
        Check for multiple SQL statements.
        
        Args:
            sql: The SQL query.
        
        Returns:
            Dict: Check result.
        """
        # Count semicolons (primary statement separator)
        # But exclude semicolons in strings
        
        semicolon_count = 0
        in_string = False
        string_char = None
        
        for i, char in enumerate(sql):
            # Track if we're inside a string
            if char in ("'", '"') and (i == 0 or sql[i-1] != '\\'):
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
            
            # Count semicolons outside strings
            if char == ';' and not in_string:
                semicolon_count += 1
        
        # Allow at most one semicolon (at the end)
        has_multiple = semicolon_count > 1 or (
            semicolon_count == 1 and not sql.rstrip().endswith(';')
        )
        
        return {
            "has_multiple": has_multiple,
            "semicolon_count": semicolon_count
        }
    
    def _check_sql_injection_patterns(self, normalized_sql: str) -> Dict:
        """
        Check for SQL injection patterns.
        
        Args:
            normalized_sql: Normalized SQL query.
        
        Returns:
            Dict: Check result with suspicious patterns found.
        """
        suspicious_patterns = []
        sql_upper = normalized_sql.upper()
        
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                suspicious_patterns.append(pattern)
                logger.warning(f"Suspicious pattern detected: {pattern}")
        
        return {
            "suspicious_patterns": suspicious_patterns
        }
    
    def _validate_select_statement(self, normalized_sql: str) -> Dict:
        """
        Validate a SELECT statement specifically.
        
        Args:
            normalized_sql: Normalized SQL query.
        
        Returns:
            Dict: Validation result.
        """
        errors = []
        
        sql_upper = normalized_sql.upper()
        
        # Must start with SELECT
        if not sql_upper.startswith("SELECT"):
            errors.append(ValidationError(
                error_type="NOT_SELECT",
                message="Statement must be a SELECT query",
                severity="critical"
            ))
            return {"is_valid": False, "errors": errors}
        
        # Check for INTO clause (file write attempt)
        if re.search(r'\bINTO\s+(OUTFILE|DUMPFILE|INFILE)\b', sql_upper):
            errors.append(ValidationError(
                error_type="FILE_OPERATION",
                message="INTO OUTFILE/DUMPFILE operations not allowed",
                severity="critical"
            ))
        
        # Check for procedure calls in SELECT
        if re.search(r'CALL\s+\w+', sql_upper):
            errors.append(ValidationError(
                error_type="PROCEDURE_CALL",
                message="Procedure calls not allowed in SELECT",
                severity="critical"
            ))
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }
    
    def _check_schema_operations(self, normalized_sql: str) -> Dict:
        """
        Check for schema modification operations.
        
        Args:
            normalized_sql: Normalized SQL query.
        
        Returns:
            Dict: Check result.
        """
        errors = []
        sql_upper = normalized_sql.upper()
        
        schema_ops = [
            (r'\bALTER\s+TABLE\b', "ALTER TABLE"),
            (r'\bALTER\s+DATABASE\b', "ALTER DATABASE"),
            (r'\bALTER\s+SCHEMA\b', "ALTER SCHEMA"),
            (r'\bCREATE\s+TABLE\b', "CREATE TABLE"),
            (r'\bCREATE\s+DATABASE\b', "CREATE DATABASE"),
            (r'\bCREATE\s+INDEX\b', "CREATE INDEX"),
            (r'\bDROP\s+TABLE\b', "DROP TABLE"),
            (r'\bDROP\s+DATABASE\b', "DROP DATABASE"),
            (r'\bDROP\s+INDEX\b', "DROP INDEX"),
            (r'\bTRUNCATE\b', "TRUNCATE"),
            (r'\bRENAME\b', "RENAME"),
        ]
        
        for pattern, operation in schema_ops:
            if re.search(pattern, sql_upper):
                errors.append(ValidationError(
                    error_type="SCHEMA_MODIFICATION",
                    message=f"{operation} operation not allowed",
                    severity="critical"
                ))
        
        return {
            "has_schema_ops": len(errors) > 0,
            "errors": errors
        }
    
    def _format_result(
        self,
        is_valid: bool,
        errors: List[ValidationError],
        warnings: List[str],
        checks_passed: List[str]
    ) -> Dict:
        """
        Format validation result for return.
        
        Args:
            is_valid: Whether validation passed.
            errors: List of validation errors.
            warnings: List of warnings.
            checks_passed: List of passed checks.
        
        Returns:
            Dict: Formatted result.
        """
        result = {
            "is_valid": is_valid,
            "error": None,
            "error_type": None,
            "warnings": warnings,
            "checks_passed": checks_passed,
            "error_count": len(errors)
        }
        
        if not is_valid and errors:
            # Get the first critical error
            critical_errors = [e for e in errors if e.severity == "critical"]
            error = critical_errors[0] if critical_errors else errors[0]
            
            result["error"] = error.message
            result["error_type"] = error.error_type
            result["all_errors"] = [str(e) for e in errors]
        
        return result
    
    def get_validation_rules(self) -> Dict:
        """
        Get detailed validation rules.
        
        Returns:
            Dict: Description of all validation rules.
        """
        return {
            "allowed_operations": ["SELECT"],
            "forbidden_operations": list(self.FORBIDDEN_STATEMENTS.keys()),
            "forbidden_operations_description": self.FORBIDDEN_STATEMENTS,
            "validation_checks": [
                "Basic format validation",
                "Forbidden statement detection",
                "Comment detection",
                "Multiple statement detection",
                "SQL injection pattern detection",
                "SELECT statement validation",
                "Schema operation detection"
            ],
            "max_query_length": 10000,
            "comment_types_blocked": ["--", "/**/", "#"]
        }


# ============ Test Cases ============
def _create_test_cases() -> List[Tuple[str, bool]]:
    """
    Create test cases for SQL validation.
    
    Returns:
        List[Tuple]: List of (sql, should_be_valid) tuples.
    """
    return [
        # Valid queries
        ("SELECT * FROM products", True),
        ("SELECT id, name FROM users WHERE id = 1", True),
        ("SELECT COUNT(*) FROM orders", True),
        ("SELECT * FROM products WHERE price > 100 AND category = 'electronics'", True),
        ("SELECT a.id, b.name FROM table_a a INNER JOIN table_b b ON a.id = b.aid", True),
        ("SELECT * FROM products ORDER BY price DESC LIMIT 10", True),
        ("SELECT DISTINCT category FROM products", True),
        ("SELECT * FROM products GROUP BY category HAVING COUNT(*) > 5", True),
        
        # Invalid queries - Forbidden operations
        ("INSERT INTO products VALUES (1, 'Widget')", False),
        ("UPDATE products SET price = 100 WHERE id = 1", False),
        ("DELETE FROM products WHERE id = 1", False),
        ("DROP TABLE products", False),
        ("ALTER TABLE products ADD COLUMN new_col INT", False),
        ("TRUNCATE TABLE products", False),
        ("CREATE TABLE new_table (id INT)", False),
        
        # Invalid queries - Comments
        ("SELECT * FROM products -- comment", False),
        ("SELECT * FROM products /* comment */", False),
        ("SELECT * FROM products # comment", False),
        
        # Invalid queries - Multiple statements
        ("SELECT * FROM products; DROP TABLE users", False),
        ("SELECT * FROM products; SELECT * FROM users", False),
        
        # Invalid queries - SQL injection patterns
        ("SELECT * FROM products WHERE id = 1 OR 1=1", False),
        ("SELECT * FROM products UNION SELECT * FROM users", False),
        ("SELECT * FROM products WHERE name = '' OR ''=''", False),
        
        # Invalid queries - Schema operations
        ("SELECT * FROM products; ALTER TABLE users ADD COLUMN admin BOOLEAN", False),
        ("SELECT * FROM products INTO OUTFILE '/tmp/data.csv'", False),
    ]


# ============ Singleton Instance ============
_validator: Optional[SQLGuardValidator] = None


def get_sql_guard_validator(strict_mode: bool = True) -> SQLGuardValidator:
    """
    Get or create the global SQL Guard Validator instance.
    
    Args:
        strict_mode: Whether to use strict validation mode.
    
    Returns:
        SQLGuardValidator: The validator instance.
    """
    global _validator
    if _validator is None:
        _validator = SQLGuardValidator(strict_mode=strict_mode)
    return _validator


# ============ Testing ============
if __name__ == "__main__":
    """
    Run tests for SQL validator.
    
    Usage:
        python -m backend.ai.validators.sql_guard
    """
    validator = SQLGuardValidator(strict_mode=True)
    test_cases = _create_test_cases()
    
    passed = 0
    failed = 0
    
    print("\n" + "="*80)
    print("SQL GUARD VALIDATOR TEST SUITE")
    print("="*80 + "\n")
    
    for sql, expected_valid in test_cases:
        result = validator.validate(sql)
        is_valid = result["is_valid"]
        
        if is_valid == expected_valid:
            status = "✓ PASS"
            passed += 1
        else:
            status = "✗ FAIL"
            failed += 1
        
        print(f"{status} | Expected: {expected_valid:5} | Got: {is_valid:5}")
        print(f"     SQL: {sql[:70]}")
        
        if not is_valid:
            print(f"     Error: {result['error']}")
        
        print()
    
    print("="*80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("="*80 + "\n")