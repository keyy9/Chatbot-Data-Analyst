"""
Evaluation and Testing Module.

Measures SQL correctness, execution success, answer quality, and detects hallucinations.
Provides comprehensive evaluation metrics for model performance.

Execution accuracy (is the generated SQL's result set actually correct)
is delegated entirely to `result_set_comparator.compare_result_sets` -
the single source of truth for that question, whenever executed gold
rows are available. The syntactic/keyword-heuristic/hallucination/schema
checks below still run, but only ever as secondary diagnostics reported
alongside the verdict - never as the headline correctness signal.
"""

import logging
import re
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from backend.ai.utils.sql_introspection import extract_tables
from backend.ai.evaluation.result_set_comparator import compare_result_sets

# ============ Setup Logging ============
logger = logging.getLogger(__name__)


class SQLCorrectness(Enum):
    """
    SQL correctness levels.
    """
    PERFECT = 1.0  # Executes correctly and returns expected results
    SYNTACTICALLY_VALID = 0.8  # Valid SQL but may not be optimal
    EXECUTABLE = 0.6  # Executes but may have logic issues
    INVALID = 0.0  # Does not execute or returns wrong results


class AnswerQuality(Enum):
    """
    Answer quality ratings.
    """
    EXCELLENT = 1.0  # Directly answers the question
    GOOD = 0.8  # Answers the question with minor issues
    ACCEPTABLE = 0.6  # Partially answers the question
    POOR = 0.3  # Tangentially related answer
    WRONG = 0.0  # Completely incorrect


class HallucinationLevel(Enum):
    """
    Levels of hallucination detection.
    """
    NONE = 1.0  # No hallucinations detected
    MINOR = 0.7  # Minor irrelevant details
    MODERATE = 0.4  # Some fabricated information
    SEVERE = 0.0  # Significantly fabricated information


@dataclass
class EvaluationMetric:
    """
    Single evaluation metric.
    
    Attributes:
        name: Metric name
        score: Score (0-1)
        weight: Weight in overall score (0-1)
        reason: Explanation for the score
        details: Additional details
    """
    name: str
    score: float
    weight: float = 1.0
    reason: str = ""
    details: Optional[Dict] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class EvaluationResult:
    """
    Complete evaluation result.
    
    Attributes:
        evaluation_id: Unique evaluation ID
        timestamp: When evaluation was performed
        user_question: The user's question
        generated_sql: The generated SQL
        expected_sql: Expected/correct SQL (for benchmarking)
        sql_correctness_score: SQL correctness (0-1)
        execution_success: Whether SQL executed successfully
        execution_time_ms: Execution time
        latency_ms: Total latency
        answer_quality_score: Quality of answer (0-1)
        hallucination_score: Hallucination level (0-1)
        schema_compliance_score: Schema compliance (0-1)
        overall_accuracy: Weighted composite diagnostic score (0-1) - NOT
            the execution-accuracy signal; see `execution_verdict` for that.
        execution_verdict: The result of executing both the generated and
            gold SQL and comparing their result sets
            (`result_set_comparator.compare_result_sets`) - the single
            source of truth for whether this answer is actually correct.
            None when gold rows weren't available to compare against
            (falls back to the legacy text-similarity heuristic instead).
        metrics: List of individual metrics
        issues: List of detected issues
        recommendations: Recommendations for improvement
    """
    evaluation_id: str
    timestamp: datetime
    user_question: str
    generated_sql: str
    expected_sql: Optional[str] = None
    sql_correctness_score: float = 0.0
    execution_success: bool = False
    execution_time_ms: float = 0.0
    latency_ms: float = 0.0
    answer_quality_score: float = 0.0
    hallucination_score: float = 1.0
    schema_compliance_score: float = 0.0
    overall_accuracy: float = 0.0
    execution_verdict: Optional[Dict] = None
    metrics: List[EvaluationMetric] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "evaluation_id": self.evaluation_id,
            "timestamp": self.timestamp.isoformat(),
            "user_question": self.user_question,
            "generated_sql": self.generated_sql,
            "expected_sql": self.expected_sql,
            "execution_verdict": self.execution_verdict,
            "scores": {
                "sql_correctness": self.sql_correctness_score,
                "answer_quality": self.answer_quality_score,
                "hallucination": self.hallucination_score,
                "schema_compliance": self.schema_compliance_score,
                "overall_accuracy": self.overall_accuracy
            },
            "execution": {
                "success": self.execution_success,
                "execution_time_ms": self.execution_time_ms,
                "latency_ms": self.latency_ms
            },
            "issues": self.issues,
            "recommendations": self.recommendations,
            "metrics": [
                {
                    "name": m.name,
                    "score": m.score,
                    "weight": m.weight,
                    "reason": m.reason
                }
                for m in self.metrics
            ]
        }


class SQLCorrectnessTester:
    """
    Evaluates SQL correctness through multiple tests.
    """
    
    # ============ Forbidden Patterns ============
    FORBIDDEN_PATTERNS = [
        (r'\bINSERT\b', "INSERT statement detected"),
        (r'\bUPDATE\b', "UPDATE statement detected"),
        (r'\bDELETE\b', "DELETE statement detected"),
        (r'\bDROP\b', "DROP statement detected"),
        (r'\bALTER\b', "ALTER statement detected"),
        (r'\bCREATE\b', "CREATE statement detected"),
    ]
    
    # ============ Required Patterns ============
    REQUIRED_SELECT_PATTERN = r'^\s*SELECT\b'
    
    def __init__(self):
        """Initialize SQL correctness tester."""
        pass
    
    def test_syntactic_validity(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        Test if SQL has valid syntax.
        
        Args:
            sql: The SQL to test.
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if not sql or len(sql.strip()) == 0:
            return False, "Empty SQL query"
        
        # Must be SELECT
        if not re.match(self.REQUIRED_SELECT_PATTERN, sql, re.IGNORECASE):
            return False, "Query must start with SELECT"
        
        # Check for forbidden patterns
        sql_upper = sql.upper()
        for pattern, message in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, sql_upper):
                return False, message
        
        # Check for balanced parentheses
        if sql.count('(') != sql.count(')'):
            return False, "Unbalanced parentheses"
        
        # Check for balanced quotes
        single_quotes = sql.count("'") - sql.count("\\'")
        double_quotes = sql.count('"') - sql.count('\\"')
        
        if single_quotes % 2 != 0:
            return False, "Unbalanced single quotes"
        if double_quotes % 2 != 0:
            return False, "Unbalanced double quotes"
        
        return True, None
    
    def test_against_reference(
        self,
        generated_sql: str,
        reference_sql: str
    ) -> Tuple[float, List[str]]:
        """
        Compare generated SQL against reference SQL.
        
        Args:
            generated_sql: The generated SQL.
            reference_sql: The reference/expected SQL.
        
        Returns:
            Tuple[float, List[str]]: (similarity_score, differences)
        """
        differences = []
        
        # Normalize both SQLs
        gen_normalized = self._normalize_sql(generated_sql)
        ref_normalized = self._normalize_sql(reference_sql)
        
        # Exact match
        if gen_normalized == ref_normalized:
            return 1.0, []
        
        # Check key components
        gen_tables = self._extract_tables(generated_sql)
        ref_tables = self._extract_tables(reference_sql)
        
        if gen_tables != ref_tables:
            differences.append(f"Tables differ: generated {gen_tables} vs reference {ref_tables}")
        
        gen_where = self._extract_where_clause(generated_sql)
        ref_where = self._extract_where_clause(reference_sql)
        
        if gen_where and ref_where and gen_where != ref_where:
            differences.append("WHERE clauses differ")
        
        # Calculate similarity based on differences
        similarity = 1.0 - (len(differences) * 0.3)  # Each diff reduces score by 0.3
        similarity = max(0.0, min(1.0, similarity))
        
        return similarity, differences
    
    def test_logical_correctness(
        self,
        sql: str,
        question: str
    ) -> Tuple[float, List[str]]:
        """
        Test if SQL logically answers the question.
        
        Args:
            sql: The SQL query.
            question: The user's question.
        
        Returns:
            Tuple[float, List[str]]: (correctness_score, issues)
        """
        issues = []
        score = 1.0
        
        sql_upper = sql.upper()
        question_lower = question.lower()
        
        # ============ Check for specific keywords ============
        
        # If question asks for "top" or "highest", should have ORDER BY DESC and LIMIT
        if any(word in question_lower for word in ["top", "highest", "best", "maximum"]):
            if "ORDER BY" not in sql_upper:
                issues.append("Missing ORDER BY for ranking query")
                score -= 0.2
            if "DESC" not in sql_upper:
                issues.append("Missing DESC for descending sort")
                score -= 0.1
            if "LIMIT" not in sql_upper:
                issues.append("Missing LIMIT for TOP N query")
                score -= 0.2
        
        # If question asks for "count", should have COUNT
        if any(word in question_lower for word in ["count", "how many", "number of"]):
            if "COUNT" not in sql_upper:
                issues.append("Missing COUNT for counting query")
                score -= 0.3
        
        # If question asks for "total", should have SUM
        if any(word in question_lower for word in ["total", "sum"]):
            if "SUM" not in sql_upper:
                issues.append("Missing SUM for aggregation query")
                score -= 0.3
        
        # If question has "compare", might need multiple queries or UNION
        if "compare" in question_lower and "WHERE" not in sql_upper:
            issues.append("Comparison query may need WHERE clause")
            score -= 0.15
        
        score = max(0.0, min(1.0, score))
        
        return score, issues
    
    def _normalize_sql(self, sql: str) -> str:
        """Normalize SQL for comparison."""
        # Remove extra whitespace
        sql = re.sub(r'\s+', ' ', sql)
        # Convert to uppercase for comparison
        sql = sql.upper().strip()
        return sql
    
    def _extract_tables(self, sql: str) -> List[str]:
        """Extract table names from SQL."""
        return extract_tables(sql)

    def _extract_where_clause(self, sql: str) -> Optional[str]:
        """Extract WHERE clause from SQL."""
        match = re.search(r'WHERE\s+(.+?)(?:GROUP BY|ORDER BY|LIMIT|$)', sql, re.IGNORECASE)
        return match.group(1) if match else None


class AnswerQualityEvaluator:
    """
    Evaluates the quality of answers based on query results.
    """
    
    def __init__(self):
        """Initialize answer quality evaluator."""
        pass
    
    def evaluate_answer_quality(
        self,
        user_question: str,
        query_result: Any,
        result_type: str  # "table", "single_value", "time_series", etc.
    ) -> Tuple[float, List[str]]:
        """
        Evaluate quality of answer to user's question.
        
        Args:
            user_question: The user's question.
            query_result: The query result data.
            result_type: Type of result.
        
        Returns:
            Tuple[float, List[str]]: (quality_score, issues)
        """
        issues = []
        score = 0.8  # Start with good score
        
        # ============ Check if result is empty ============
        if query_result is None:
            return 0.0, ["Query returned no results"]
        
        if isinstance(query_result, list) and len(query_result) == 0:
            return 0.0, ["Query returned no rows"]
        
        # ============ Check result relevance ============
        question_keywords = self._extract_keywords(user_question)
        result_keywords = self._extract_keywords(str(query_result))
        
        # Check keyword overlap
        keyword_overlap = len(set(question_keywords) & set(result_keywords))
        if keyword_overlap == 0:
            issues.append("Result keywords don't match question keywords")
            score -= 0.3
        
        # ============ Check result structure ============
        if isinstance(query_result, list):
            if len(query_result) == 1:
                # Single result
                if "count" in question_keywords or "how many" in user_question.lower():
                    score = 0.9  # Good for counting
                else:
                    score = 0.7  # Acceptable for single result
            elif len(query_result) > 1:
                # Multiple results
                if "list" in question_keywords or "all" in question_keywords:
                    score = 0.95  # Good for listing
                else:
                    score = 0.8  # Acceptable for multiple results
        
        return score, issues
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Remove common stop words
        stop_words = {"the", "a", "an", "and", "or", "is", "are", "to", "from", "of"}
        
        # Extract words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter stop words and short words
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords


class HallucinationDetector:
    """
    Detects hallucinations in generated SQL and results.
    """
    
    # ============ Suspicious Patterns ============
    SUSPICIOUS_PATTERNS = [
        (r"FROM\s+\w+_\d+_temp", "Suspicious temporary table"),
        (r"SELECT\s+\*\s+FROM\s+\(\s*SELECT\s+\*", "Nested SELECT * patterns"),
        (r"WHERE\s+\d+\s*=\s*\d+", "Meaningless WHERE conditions"),
        (r"UNION\s+ALL.*?FROM\s+information_schema", "Schema introspection attempt"),
    ]
    
    def __init__(self):
        """Initialize hallucination detector."""
        pass
    
    def detect_hallucinations(
        self,
        sql: str,
        question: str,
        available_tables: List[str],
        available_columns: Dict[str, List[str]]
    ) -> Tuple[float, List[str]]:
        """
        Detect hallucinations in generated SQL.
        
        Args:
            sql: The generated SQL.
            question: The user's question.
            available_tables: List of available tables.
            available_columns: Dict of available columns per table.
        
        Returns:
            Tuple[float, List[str]]: (hallucination_score, hallucinations)
                hallucination_score: 1.0 = no hallucinations, 0.0 = severe hallucinations
        """
        hallucinations = []
        score = 1.0
        
        # ============ Check for non-existent tables ============
        extracted_tables = self._extract_tables(sql)
        
        for table in extracted_tables:
            if table.lower() not in [t.lower() for t in available_tables]:
                hallucinations.append(f"Non-existent table referenced: {table}")
                score -= 0.3
        
        # ============ Check for non-existent columns ============
        extracted_columns = self._extract_columns(sql)
        
        for table, cols in extracted_columns.items():
            if table.lower() in [t.lower() for t in available_tables]:
                available_cols = available_columns.get(table.lower(), [])
                available_cols_lower = [c.lower() for c in available_cols]
                
                for col in cols:
                    if col.lower() not in available_cols_lower and col != "*":
                        hallucinations.append(f"Non-existent column: {table}.{col}")
                        score -= 0.25
        
        # ============ Check for suspicious patterns ============
        for pattern, description in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                hallucinations.append(description)
                score -= 0.2
        
        # ============ Check for question-SQL mismatch ============
        question_entities = self._extract_entities(question)
        sql_entities = self._extract_entities(sql)
        
        # If question mentions specific entities not in SQL, might be hallucination
        for entity in question_entities:
            if entity and entity.lower() not in sql_entities:
                # This might be OK (e.g., entity is in WHERE clause as value)
                pass
        
        score = max(0.0, min(1.0, score))
        
        return score, hallucinations
    
    def _extract_tables(self, sql: str) -> List[str]:
        """Extract table names from SQL."""
        return extract_tables(sql)

    def _extract_columns(self, sql: str) -> Dict[str, List[str]]:
        """Extract columns used in SQL by table."""
        columns = {}
        
        # Look for table.column patterns
        pattern = r'(\w+)\.(\w+)'
        matches = re.findall(pattern, sql)
        
        for table, col in matches:
            if table not in columns:
                columns[table] = []
            columns[table].append(col)
        
        return columns
    
    def _extract_entities(self, text: str) -> List[str]:
        """Extract entities (proper nouns, capitalized words)."""
        # Simple approach: look for capitalized words
        pattern = r'\b[A-Z][a-z]+\b'
        matches = re.findall(pattern, text)
        return matches


class SchemaComplianceChecker:
    """
    Checks SQL compliance with provided schema.
    """
    
    def __init__(self):
        """Initialize schema compliance checker."""
        pass
    
    def check_compliance(
        self,
        sql: str,
        available_tables: List[str],
        available_columns: Dict[str, List[str]]
    ) -> Tuple[float, List[str]]:
        """
        Check if SQL complies with schema.
        
        Args:
            sql: The SQL query.
            available_tables: Available tables.
            available_columns: Available columns per table.
        
        Returns:
            Tuple[float, List[str]]: (compliance_score, issues)
        """
        issues = []
        score = 1.0
        
        # ============ Extract SQL components ============
        extracted_tables = self._extract_tables(sql)
        
        # ============ Check table existence ============
        available_tables_lower = [t.lower() for t in available_tables]
        
        for table in extracted_tables:
            if table.lower() not in available_tables_lower:
                issues.append(f"Table not in schema: {table}")
                score -= 0.3
        
        # ============ Check column existence ============
        # This is simplified; a full implementation would parse SELECT columns
        for table in extracted_tables:
            if table.lower() in available_tables_lower:
                available_cols = available_columns.get(table.lower(), [])
                available_cols_lower = [c.lower() for c in available_cols]
                
                # Check for SELECT * (always valid)
                if re.search(rf'SELECT\s+\*\s+FROM\s+{table}', sql, re.IGNORECASE):
                    continue
        
        score = max(0.0, min(1.0, score))
        
        return score, issues
    
    def _extract_tables(self, sql: str) -> List[str]:
        """Extract table names from SQL."""
        return extract_tables(sql)


class ModelEvaluator:
    """
    High-level model evaluator combining all evaluation components.
    """
    
    def __init__(self):
        """Initialize model evaluator."""
        self.sql_tester = SQLCorrectnessTester()
        self.answer_evaluator = AnswerQualityEvaluator()
        self.hallucination_detector = HallucinationDetector()
        self.schema_checker = SchemaComplianceChecker()
        
        logger.info("ModelEvaluator initialized")
    
    def evaluate(
        self,
        user_question: str,
        generated_sql: str,
        query_result: Any,
        execution_success: bool,
        execution_time_ms: float,
        latency_ms: float,
        expected_sql: Optional[str] = None,
        available_tables: Optional[List[str]] = None,
        available_columns: Optional[Dict[str, List[str]]] = None,
        result_type: str = "table",
        gold_rows: Optional[List[Dict]] = None
    ) -> EvaluationResult:
        """
        Perform comprehensive evaluation.

        Args:
            user_question: The user's question.
            generated_sql: The generated SQL.
            query_result: The generated SQL's result rows.
            execution_success: Whether SQL executed successfully.
            execution_time_ms: Execution time.
            latency_ms: Total latency.
            expected_sql: Optional expected (gold) SQL for comparison.
            available_tables: Available tables in schema.
            available_columns: Available columns per table.
            result_type: Type of result.
            gold_rows: The gold SQL's executed result rows, if available.
                When both this and `expected_sql` are provided, execution
                accuracy is computed by actually comparing result sets
                (`result_set_comparator.compare_result_sets`) rather than
                the legacy SQL-text-similarity heuristic below.

        Returns:
            EvaluationResult: Complete evaluation result.
        """
        import uuid
        from datetime import datetime

        evaluation_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()

        metrics = []
        issues = []
        recommendations = []

        # ============ Test SQL Correctness ============
        syntactic_valid, syntactic_error = self.sql_tester.test_syntactic_validity(generated_sql)
        execution_verdict = None

        if not syntactic_valid:
            sql_correctness = 0.0
            issues.append(f"Syntax error: {syntactic_error}")
        elif expected_sql and gold_rows is not None:
            # ============ Execution accuracy: the headline signal ============
            verdict = compare_result_sets(
                generated_rows=query_result if isinstance(query_result, list) else [],
                gold_rows=gold_rows,
                gold_sql=expected_sql
            )
            execution_verdict = {
                "is_match": verdict.is_match,
                "category": verdict.category,
                "reason": verdict.reason
            }
            sql_correctness = 1.0 if verdict.is_match else 0.0
            if not verdict.is_match:
                issues.append(f"Execution mismatch ({verdict.category}): {verdict.reason}")

            # Legacy heuristics still run, but purely as diagnostics from
            # here on - they never touch sql_correctness when a real
            # execution verdict is available.
            _, diag_differences = self.sql_tester.test_against_reference(generated_sql, expected_sql)
            _, diag_logical_issues = self.sql_tester.test_logical_correctness(generated_sql, user_question)
            issues.extend(f"[diagnostic] {d}" for d in diag_differences)
            issues.extend(f"[diagnostic] {d}" for d in diag_logical_issues)
        elif expected_sql:
            # No executed gold rows available (e.g. gold SQL failed to run) -
            # fall back to the legacy text-similarity heuristic.
            similarity, differences = self.sql_tester.test_against_reference(generated_sql, expected_sql)
            logical_score, logical_issues = self.sql_tester.test_logical_correctness(
                generated_sql,
                user_question
            )
            sql_correctness = (similarity + logical_score) / 2
            issues.extend(logical_issues)
            issues.extend(differences)
        else:
            logical_score, logical_issues = self.sql_tester.test_logical_correctness(
                generated_sql,
                user_question
            )
            sql_correctness = logical_score
            issues.extend(logical_issues)
        
        metrics.append(EvaluationMetric(
            name="SQL Correctness",
            score=sql_correctness,
            weight=0.35,
            reason=(
                "Execution accuracy (result-set comparison against gold SQL)"
                if execution_verdict is not None else
                "SQL validity and logical correctness (heuristic - no gold rows available)"
            ),
            details={
                "syntactically_valid": syntactic_valid,
                "logical_correctness": sql_correctness,
                "execution_verdict": execution_verdict
            }
        ))
        
        # ============ Test Answer Quality ============
        answer_quality, quality_issues = self.answer_evaluator.evaluate_answer_quality(
            user_question,
            query_result,
            result_type
        )
        
        issues.extend(quality_issues)
        
        metrics.append(EvaluationMetric(
            name="Answer Quality",
            score=answer_quality,
            weight=0.25,
            reason="Relevance and completeness of answer"
        ))
        
        # ============ Detect Hallucinations ============
        available_tables = available_tables or []
        available_columns = available_columns or {}
        
        hallucination_score, hallucinations = self.hallucination_detector.detect_hallucinations(
            generated_sql,
            user_question,
            available_tables,
            available_columns
        )
        
        issues.extend(hallucinations)
        
        metrics.append(EvaluationMetric(
            name="Hallucination Detection",
            score=hallucination_score,
            weight=0.20,
            reason="No fabricated tables or columns"
        ))
        
        # ============ Check Schema Compliance ============
        schema_compliance, schema_issues = self.schema_checker.check_compliance(
            generated_sql,
            available_tables,
            available_columns
        )
        
        issues.extend(schema_issues)
        
        metrics.append(EvaluationMetric(
            name="Schema Compliance",
            score=schema_compliance,
            weight=0.15,
            reason="Compliance with available schema"
        ))
        
        # ============ Check Execution Success ============
        execution_score = 1.0 if execution_success else 0.0
        
        metrics.append(EvaluationMetric(
            name="Execution Success",
            score=execution_score,
            weight=0.05,
            reason="SQL executed successfully"
        ))
        
        # ============ Calculate Overall Accuracy ============
        overall_accuracy = sum(m.score * m.weight for m in metrics) / sum(m.weight for m in metrics)
        
        # ============ Generate Recommendations ============
        if sql_correctness < 0.8:
            recommendations.append("Review and refine SQL generation prompt")
        
        if answer_quality < 0.7:
            recommendations.append("Improve question interpretation logic")
        
        if hallucination_score < 0.8:
            recommendations.append("Strengthen schema awareness in LLM prompt")
        
        if schema_compliance < 0.8:
            recommendations.append("Ensure all tables and columns are validated against schema")
        
        if execution_time_ms > 5000:
            recommendations.append("Optimize SQL query for better performance")
        
        # ============ Create Result ============
        result = EvaluationResult(
            evaluation_id=evaluation_id,
            timestamp=timestamp,
            user_question=user_question,
            generated_sql=generated_sql,
            expected_sql=expected_sql,
            sql_correctness_score=sql_correctness,
            execution_success=execution_success,
            execution_time_ms=execution_time_ms,
            latency_ms=latency_ms,
            answer_quality_score=answer_quality,
            hallucination_score=hallucination_score,
            schema_compliance_score=schema_compliance,
            overall_accuracy=overall_accuracy,
            execution_verdict=execution_verdict,
            metrics=metrics,
            issues=issues,
            recommendations=recommendations
        )
        
        logger.info(
            f"Evaluation complete: {evaluation_id} | "
            f"Accuracy: {overall_accuracy:.2%} | "
            f"Issues: {len(issues)}"
        )
        
        return result
    
    def batch_evaluate(
        self,
        test_cases: List[Dict[str, Any]],
        available_tables: Optional[List[str]] = None,
        available_columns: Optional[Dict[str, List[str]]] = None
    ) -> Tuple[List[EvaluationResult], Dict]:
        """
        Evaluate multiple test cases.
        
        Args:
            test_cases: List of test case dicts with required fields.
            available_tables: Available tables.
            available_columns: Available columns.
        
        Returns:
            Tuple[List[EvaluationResult], Dict]: Results and summary stats.
        """
        results = []
        
        for test_case in test_cases:
            result = self.evaluate(
                user_question=test_case["user_question"],
                generated_sql=test_case["generated_sql"],
                query_result=test_case.get("query_result"),
                execution_success=test_case.get("execution_success", True),
                execution_time_ms=test_case.get("execution_time_ms", 0),
                latency_ms=test_case.get("latency_ms", 0),
                expected_sql=test_case.get("expected_sql"),
                available_tables=available_tables,
                available_columns=available_columns,
                result_type=test_case.get("result_type", "table")
            )
            
            results.append(result)
        
        # Calculate summary statistics
        if results:
            avg_accuracy = sum(r.overall_accuracy for r in results) / len(results)
            avg_execution_time = sum(r.execution_time_ms for r in results) / len(results)
            success_rate = sum(1 for r in results if r.execution_success) / len(results)
            
            summary = {
                "total_evaluations": len(results),
                "average_accuracy": avg_accuracy,
                "average_execution_time_ms": avg_execution_time,
                "execution_success_rate": success_rate,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            summary = {}
        
        return results, summary


# ============ Singleton Instance ============
_model_evaluator: Optional[ModelEvaluator] = None


def get_model_evaluator() -> ModelEvaluator:
    """
    Get or create the global model evaluator instance.
    
    Returns:
        ModelEvaluator: The evaluator instance.
    """
    global _model_evaluator
    if _model_evaluator is None:
        _model_evaluator = ModelEvaluator()
    return _model_evaluator