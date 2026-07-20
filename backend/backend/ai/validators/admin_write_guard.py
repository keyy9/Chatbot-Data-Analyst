"""
Admin Write SQL Guard.

`SQLGuardValidator` (sql_guard.py) is hard-coded read-only: it rejects any
statement that isn't SELECT, and blanket-forbids INSERT/UPDATE/DELETE for
every caller regardless of role. That's correct for the user-facing NL
pipeline, but the admin NL-to-write endpoint needs an admin's generated
INSERT/UPDATE/DELETE to actually pass basic SQL hygiene checks so it can
reach the propose -> confirm flow (the same human-in-the-loop review that
already gates the structured create/update/delete endpoints).

This validator reuses every hygiene check from the base validator
(comments, multiple statements, injection patterns, schema-modification
detection) and only replaces the two checks that are unconditionally
read-only: the forbidden-statement list and the "must start with SELECT"
gate. It still refuses DROP/ALTER/TRUNCATE/CREATE/GRANT/REVOKE/etc., and
additionally requires a WHERE clause on UPDATE/DELETE so a generated
statement can't blanket-modify a whole table.
"""

import re
import logging
from typing import Dict

from backend.ai.validators.sql_guard import SQLGuardValidator, ValidationError

logger = logging.getLogger(__name__)


class AdminWriteSQLGuard(SQLGuardValidator):
    """SQL guard for LLM-generated admin statements (SELECT + DML allowed)."""

    # Same destructive/schema operations as the base guard, minus INSERT/UPDATE/DELETE.
    FORBIDDEN_STATEMENTS = {
        k: v for k, v in SQLGuardValidator.FORBIDDEN_STATEMENTS.items()
        if k not in ("INSERT", "UPDATE", "DELETE")
    }

    ALLOWED_LEADING_STATEMENTS = {"SELECT", "INSERT", "UPDATE", "DELETE"}
    REQUIRES_WHERE = {"UPDATE", "DELETE"}

    def validate(self, sql_query: str) -> Dict:
        """Validate an admin-write SQL statement (SELECT/INSERT/UPDATE/DELETE)."""
        errors = []
        warnings = []
        checks_passed = []

        if not sql_query or len(sql_query.strip()) == 0:
            errors.append(ValidationError("EMPTY_QUERY", "SQL query is empty"))
            return self._format_result(False, errors, warnings, checks_passed)

        if len(sql_query) > 10000:
            errors.append(ValidationError("QUERY_TOO_LONG", "SQL query exceeds maximum length (10000 characters)"))
            return self._format_result(False, errors, warnings, checks_passed)

        checks_passed.append("Basic format check passed")

        normalized_sql = self._normalize_sql(sql_query)
        sql_upper = normalized_sql.upper()

        # ============ Forbidden (destructive/schema) statements ============
        forbidden_check = self._check_forbidden_statements(normalized_sql)
        if forbidden_check["has_forbidden"]:
            errors.extend(forbidden_check["errors"])
        else:
            checks_passed.append("No forbidden SQL statements detected")

        # ============ Comments ============
        comment_check = self._check_for_comments(sql_query)
        if comment_check["has_comments"]:
            errors.append(ValidationError(
                "COMMENTS_DETECTED",
                f"SQL comments detected: {comment_check['comment_types']}. Not allowed for security reasons."
            ))
        else:
            checks_passed.append("No comments detected")

        # ============ Multiple statements ============
        multi_stmt_check = self._check_multiple_statements(sql_query)
        if multi_stmt_check["has_multiple"]:
            errors.append(ValidationError("MULTIPLE_STATEMENTS", "Only single statements are allowed"))
        else:
            checks_passed.append("Single statement validation passed")

        # ============ Injection patterns ============
        injection_check = self._check_sql_injection_patterns(normalized_sql)
        if injection_check["suspicious_patterns"]:
            for pattern in injection_check["suspicious_patterns"]:
                errors.append(ValidationError("SQL_INJECTION_DETECTED", f"Suspicious pattern detected: {pattern}"))
        else:
            checks_passed.append("No SQL injection patterns detected")

        # ============ Leading statement must be SELECT/INSERT/UPDATE/DELETE ============
        leading_statement = next(
            (stmt for stmt in self.ALLOWED_LEADING_STATEMENTS if sql_upper.startswith(stmt)),
            None
        )
        if not leading_statement:
            errors.append(ValidationError(
                "STATEMENT_NOT_ALLOWED",
                "Statement must be SELECT, INSERT, UPDATE, or DELETE"
            ))
        else:
            checks_passed.append(f"{leading_statement} statement allowed for admin")

            if leading_statement in self.REQUIRES_WHERE and not re.search(r'\bWHERE\b', sql_upper):
                errors.append(ValidationError(
                    "MISSING_WHERE_CLAUSE",
                    f"{leading_statement} statements must include a WHERE clause "
                    "(a whole-table write is not allowed without an explicit filter)"
                ))

        # ============ Schema modification ============
        schema_check = self._check_schema_operations(normalized_sql)
        if schema_check["has_schema_ops"]:
            errors.extend(schema_check["errors"])
        else:
            checks_passed.append("No schema modification operations detected")

        is_valid = len(errors) == 0

        if is_valid:
            logger.info(f"Admin write SQL validation PASSED. Checks passed: {len(checks_passed)}")
        else:
            logger.warning(f"Admin write SQL validation FAILED. Errors: {len(errors)}")

        return self._format_result(is_valid, errors, warnings, checks_passed)


_admin_write_guard: "AdminWriteSQLGuard | None" = None


def get_admin_write_guard() -> AdminWriteSQLGuard:
    """Get or create the global admin write SQL guard instance."""
    global _admin_write_guard
    if _admin_write_guard is None:
        _admin_write_guard = AdminWriteSQLGuard(strict_mode=True)
    return _admin_write_guard
