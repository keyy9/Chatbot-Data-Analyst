"""
Monitoring and Logging Module.

Tracks LLM API calls, performance metrics, costs, and errors.
Provides comprehensive monitoring utilities for production deployments.
"""

import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
from pathlib import Path

# ============ Setup Logging ============
logger = logging.getLogger(__name__)


class EventType(Enum):
    """
    Enumeration of monitored event types.
    """
    SQL_GENERATION = "sql_generation"
    SQL_VALIDATION = "sql_validation"
    SQL_EXECUTION = "sql_execution"
    EXPLANATION_GENERATION = "explanation_generation"
    CHART_RECOMMENDATION = "chart_recommendation"
    CLARIFICATION_REQUEST = "clarification_request"
    API_CALL = "api_call"
    ERROR = "error"
    WARNING = "warning"


class EventSeverity(Enum):
    """
    Severity levels for events.
    """
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MonitoringEvent:
    """
    Represents a monitored event.
    
    Attributes:
        event_id: Unique event identifier
        event_type: Type of event
        timestamp: When the event occurred
        user_id: User who triggered the event
        session_id: Session identifier
        severity: Event severity level
        message: Event message
        duration_ms: Duration in milliseconds
        status: Success/failure status
        error: Error message if applicable
        metadata: Additional metadata (context-dependent)
        model: LLM model used (if applicable)
        input_tokens: Number of input tokens (if LLM)
        output_tokens: Number of output tokens (if LLM)
        estimated_cost: Estimated cost in USD (if LLM)
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.API_CALL
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    severity: EventSeverity = EventSeverity.INFO
    message: str = ""
    duration_ms: float = 0.0
    status: str = "success"  # success, failure, partial
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    model: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert event to dictionary."""
        data = asdict(self)
        data["event_type"] = self.event_type.value
        data["severity"] = self.severity.value
        data["timestamp"] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert event to JSON."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class LLMCallMetrics:
    """
    Metrics for an LLM API call.
    
    Attributes:
        model: Model name
        input_tokens: Input tokens
        output_tokens: Output tokens
        total_tokens: Total tokens
        latency_ms: API latency
        temperature: Temperature setting
        max_tokens: Max tokens setting
        finish_reason: Why generation finished
        estimated_cost: Estimated cost
        success: Whether call succeeded
        error_type: Type of error if failed
    """
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float
    temperature: float
    max_tokens: int
    finish_reason: str
    estimated_cost: float
    success: bool
    error_type: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class MonitoringLogger:
    """
    Central monitoring and logging system.
    
    Features:
    - Event tracking with unique IDs
    - Performance metrics collection
    - Cost tracking and estimation
    - Error aggregation
    - Session management
    - File-based logging
    """
    
    def __init__(
        self,
        log_file: Optional[str] = None,
        enable_file_logging: bool = True,
        enable_console_logging: bool = True,
        log_level: str = "INFO"
    ):
        """
        Initialize monitoring logger.
        
        Args:
            log_file: Path to log file (if None, uses default).
            enable_file_logging: Whether to write to file.
            enable_console_logging: Whether to log to console.
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
        """
        self.log_file = log_file or "ai_monitoring.log"
        self.enable_file_logging = enable_file_logging
        self.enable_console_logging = enable_console_logging
        
        # Storage for events (in-memory, for production use database)
        self.events: List[MonitoringEvent] = []
        self.metrics_cache: Dict[str, List[LLMCallMetrics]] = {}
        
        # Setup logging
        self._setup_logging(log_level)
        
        logger.info("MonitoringLogger initialized")
    
    def _setup_logging(self, log_level: str):
        """
        Setup Python logging.
        
        Args:
            log_level: Logging level.
        """
        log_level_enum = getattr(logging, log_level.upper(), logging.INFO)
        
        # Create logger
        monitoring_logger = logging.getLogger("ai_monitoring")
        monitoring_logger.setLevel(log_level_enum)
        
        # Console handler
        if self.enable_console_logging:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level_enum)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            monitoring_logger.addHandler(console_handler)
        
        # File handler
        if self.enable_file_logging:
            try:
                # Create logs directory if needed
                log_path = Path(self.log_file)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                
                file_handler = logging.FileHandler(self.log_file)
                file_handler.setLevel(log_level_enum)
                
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                file_handler.setFormatter(formatter)
                monitoring_logger.addHandler(file_handler)
            except Exception as e:
                logger.warning(f"Failed to setup file logging: {str(e)}")
    
    def log_event(
        self,
        event_type: EventType,
        message: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        severity: EventSeverity = EventSeverity.INFO,
        duration_ms: float = 0.0,
        status: str = "success",
        error: Optional[str] = None,
        metadata: Optional[Dict] = None,
        **kwargs
    ) -> MonitoringEvent:
        """
        Log a monitoring event.
        
        Args:
            event_type: Type of event.
            message: Event message.
            user_id: User identifier.
            session_id: Session identifier.
            severity: Event severity.
            duration_ms: Duration in milliseconds.
            status: Status (success/failure/partial).
            error: Error message if applicable.
            metadata: Additional metadata.
            **kwargs: Additional fields (model, tokens, cost, etc.).
        
        Returns:
            MonitoringEvent: The logged event.
        """
        event = MonitoringEvent(
            event_type=event_type,
            message=message,
            user_id=user_id,
            session_id=session_id,
            severity=severity,
            duration_ms=duration_ms,
            status=status,
            error=error,
            metadata=metadata or {},
            model=kwargs.get("model"),
            input_tokens=kwargs.get("input_tokens", 0),
            output_tokens=kwargs.get("output_tokens", 0),
            estimated_cost=kwargs.get("estimated_cost", 0.0)
        )
        
        self.events.append(event)
        
        # Log to Python logging
        log_func = {
            EventSeverity.INFO: logger.info,
            EventSeverity.WARNING: logger.warning,
            EventSeverity.ERROR: logger.error,
            EventSeverity.CRITICAL: logger.critical
        }.get(severity, logger.info)
        
        log_func(
            f"[{event_type.value}] {message} "
            f"(duration={duration_ms}ms, status={status}, "
            f"tokens={event.input_tokens + event.output_tokens})"
        )
        
        return event
    
    def log_llm_call(
        self,
        user_id: Optional[str],
        session_id: Optional[str],
        model: str,
        prompt_type: str,  # "sql", "explanation", "chart"
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        temperature: float,
        max_tokens: int,
        finish_reason: str,
        estimated_cost: float,
        success: bool = True,
        error_type: Optional[str] = None
    ) -> MonitoringEvent:
        """
        Log an LLM API call with detailed metrics.
        
        Args:
            user_id: User identifier.
            session_id: Session identifier.
            model: Model name.
            prompt_type: Type of prompt (sql, explanation, chart).
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.
            latency_ms: API call latency.
            temperature: Temperature setting.
            max_tokens: Max tokens setting.
            finish_reason: Why generation finished.
            estimated_cost: Estimated cost in USD.
            success: Whether call succeeded.
            error_type: Error type if failed.
        
        Returns:
            MonitoringEvent: The logged event.
        """
        status = "success" if success else "failure"
        severity = EventSeverity.ERROR if not success else EventSeverity.INFO
        
        return self.log_event(
            event_type=EventType.API_CALL,
            message=f"LLM call for {prompt_type} generation",
            user_id=user_id,
            session_id=session_id,
            severity=severity,
            duration_ms=latency_ms,
            status=status,
            error=error_type,
            metadata={
                "prompt_type": prompt_type,
                "temperature": temperature,
                "finish_reason": finish_reason
            },
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=estimated_cost
        )
    
    def log_sql_generation(
        self,
        user_id: Optional[str],
        session_id: Optional[str],
        user_question: str,
        generated_sql: Optional[str],
        is_valid: bool,
        is_ambiguous: bool,
        duration_ms: float,
        llm_metrics: Optional[LLMCallMetrics] = None,
        error: Optional[str] = None
    ) -> MonitoringEvent:
        """
        Log SQL generation event.
        
        Args:
            user_id: User identifier.
            session_id: Session identifier.
            user_question: The user's question.
            generated_sql: The generated SQL (if successful).
            is_valid: Whether SQL passed validation.
            is_ambiguous: Whether question was ambiguous.
            duration_ms: Generation duration.
            llm_metrics: LLM call metrics.
            error: Error message if failed.
        
        Returns:
            MonitoringEvent: The logged event.
        """
        status = "success" if (is_valid and not is_ambiguous) else "partial" if is_ambiguous else "failure"
        
        return self.log_event(
            event_type=EventType.SQL_GENERATION,
            message=f"SQL generation: {user_question[:50]}...",
            user_id=user_id,
            session_id=session_id,
            severity=EventSeverity.INFO if status == "success" else EventSeverity.WARNING,
            duration_ms=duration_ms,
            status=status,
            error=error,
            metadata={
                "user_question": user_question,
                "sql_length": len(generated_sql) if generated_sql else 0,
                "is_valid": is_valid,
                "is_ambiguous": is_ambiguous,
                "llm_metrics": llm_metrics.to_dict() if llm_metrics else None
            },
            model=llm_metrics.model if llm_metrics else None,
            input_tokens=llm_metrics.input_tokens if llm_metrics else 0,
            output_tokens=llm_metrics.output_tokens if llm_metrics else 0,
            estimated_cost=llm_metrics.estimated_cost if llm_metrics else 0.0
        )
    
    def log_sql_validation(
        self,
        user_id: Optional[str],
        session_id: Optional[str],
        sql: str,
        is_valid: bool,
        error: Optional[str] = None,
        duration_ms: float = 0.0
    ) -> MonitoringEvent:
        """
        Log SQL validation event.
        
        Args:
            user_id: User identifier.
            session_id: Session identifier.
            sql: The SQL to validate.
            is_valid: Whether SQL is valid.
            error: Validation error if invalid.
            duration_ms: Validation duration.
        
        Returns:
            MonitoringEvent: The logged event.
        """
        return self.log_event(
            event_type=EventType.SQL_VALIDATION,
            message=f"SQL validation: {'PASSED' if is_valid else 'FAILED'}",
            user_id=user_id,
            session_id=session_id,
            severity=EventSeverity.INFO if is_valid else EventSeverity.WARNING,
            duration_ms=duration_ms,
            status="success" if is_valid else "failure",
            error=error,
            metadata={
                "sql_length": len(sql),
                "is_valid": is_valid
            }
        )
    
    def log_error(
        self,
        user_id: Optional[str],
        session_id: Optional[str],
        error_message: str,
        error_type: str,
        component: str,
        duration_ms: float = 0.0,
        metadata: Optional[Dict] = None
    ) -> MonitoringEvent:
        """
        Log an error event.
        
        Args:
            user_id: User identifier.
            session_id: Session identifier.
            error_message: Error message.
            error_type: Type of error.
            component: Component where error occurred.
            duration_ms: Duration when error occurred.
            metadata: Additional metadata.
        
        Returns:
            MonitoringEvent: The logged event.
        """
        return self.log_event(
            event_type=EventType.ERROR,
            message=f"Error in {component}: {error_message}",
            user_id=user_id,
            session_id=session_id,
            severity=EventSeverity.ERROR,
            duration_ms=duration_ms,
            status="failure",
            error=error_message,
            metadata=metadata or {},
        )
    
    def get_metrics_summary(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        time_range_minutes: Optional[int] = None
    ) -> Dict:
        """
        Get metrics summary for reporting.
        
        Args:
            user_id: Filter by user ID.
            session_id: Filter by session ID.
            time_range_minutes: Only include events from last N minutes.
        
        Returns:
            Dict: Metrics summary.
        """
        # Filter events
        filtered_events = self.events
        
        if user_id:
            filtered_events = [e for e in filtered_events if e.user_id == user_id]
        
        if session_id:
            filtered_events = [e for e in filtered_events if e.session_id == session_id]
        
        if time_range_minutes:
            cutoff_time = datetime.utcnow() - timedelta(minutes=time_range_minutes)
            filtered_events = [e for e in filtered_events if e.timestamp >= cutoff_time]
        
        if not filtered_events:
            return {"total_events": 0, "message": "No events found"}
        
        # Calculate metrics
        total_events = len(filtered_events)
        success_count = len([e for e in filtered_events if e.status == "success"])
        error_count = len([e for e in filtered_events if e.status == "failure"])
        
        total_duration = sum(e.duration_ms for e in filtered_events)
        avg_duration = total_duration / total_events if total_events > 0 else 0
        
        total_input_tokens = sum(e.input_tokens for e in filtered_events)
        total_output_tokens = sum(e.output_tokens for e in filtered_events)
        total_cost = sum(e.estimated_cost for e in filtered_events)
        
        # Event type breakdown
        event_types = {}
        for event in filtered_events:
            event_type = event.event_type.value
            if event_type not in event_types:
                event_types[event_type] = 0
            event_types[event_type] += 1
        
        # Error breakdown
        errors = {}
        for event in filtered_events:
            if event.error:
                error_type = event.error[:50]  # Truncate
                if error_type not in errors:
                    errors[error_type] = 0
                errors[error_type] += 1
        
        return {
            "total_events": total_events,
            "success_count": success_count,
            "error_count": error_count,
            "success_rate": (success_count / total_events * 100) if total_events > 0 else 0,
            "total_duration_ms": total_duration,
            "avg_duration_ms": avg_duration,
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "total_cost_usd": total_cost,
            "event_types": event_types,
            "errors": errors,
            "time_range_minutes": time_range_minutes
        }
    
    def get_events(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        severity: Optional[EventSeverity] = None,
        limit: int = 100
    ) -> List[MonitoringEvent]:
        """
        Get events with filtering.
        
        Args:
            user_id: Filter by user ID.
            session_id: Filter by session ID.
            event_type: Filter by event type.
            severity: Filter by severity.
            limit: Maximum events to return.
        
        Returns:
            List[MonitoringEvent]: Filtered events.
        """
        events = self.events
        
        if user_id:
            events = [e for e in events if e.user_id == user_id]
        
        if session_id:
            events = [e for e in events if e.session_id == session_id]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if severity:
            events = [e for e in events if e.severity == severity]
        
        # Return most recent first
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    def export_events_json(self, file_path: str):
        """
        Export events to JSON file.
        
        Args:
            file_path: Path to export to.
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(
                    [e.to_dict() for e in self.events],
                    f,
                    indent=2,
                    default=str
                )
            logger.info(f"Exported {len(self.events)} events to {file_path}")
        except Exception as e:
            logger.error(f"Failed to export events: {str(e)}")
    
    def export_metrics_json(self, file_path: str):
        """
        Export metrics summary to JSON file.
        
        Args:
            file_path: Path to export to.
        """
        try:
            metrics = self.get_metrics_summary()
            with open(file_path, 'w') as f:
                json.dump(metrics, f, indent=2, default=str)
            logger.info(f"Exported metrics to {file_path}")
        except Exception as e:
            logger.error(f"Failed to export metrics: {str(e)}")
    
    def clear_old_events(self, days: int = 7):
        """
        Clear events older than N days.
        
        Args:
            days: Number of days to keep.
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        original_count = len(self.events)
        
        self.events = [e for e in self.events if e.timestamp >= cutoff_time]
        
        removed_count = original_count - len(self.events)
        logger.info(f"Cleared {removed_count} events older than {days} days")


class PerformanceMonitor:
    """
    Monitors performance metrics across the system.
    """
    
    def __init__(self):
        """Initialize performance monitor."""
        self.metrics: List[Dict] = []
    
    def record_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "",
        tags: Optional[Dict] = None
    ):
        """
        Record a performance metric.
        
        Args:
            metric_name: Name of the metric.
            value: Metric value.
            unit: Unit of measurement.
            tags: Optional tags for categorization.
        """
        metric = {
            "name": metric_name,
            "value": value,
            "unit": unit,
            "timestamp": datetime.utcnow().isoformat(),
            "tags": tags or {}
        }
        
        self.metrics.append(metric)
    
    def get_metric_summary(self, metric_name: str) -> Optional[Dict]:
        """
        Get summary for a metric.
        
        Args:
            metric_name: Name of the metric.
        
        Returns:
            Dict: Summary statistics.
        """
        values = [m["value"] for m in self.metrics if m["name"] == metric_name]
        
        if not values:
            return None
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "total": sum(values)
        }


# ============ Singleton Instance ============
_monitoring_logger: Optional[MonitoringLogger] = None


def get_monitoring_logger() -> MonitoringLogger:
    """
    Get or create the global monitoring logger instance.
    
    Returns:
        MonitoringLogger: The monitoring logger instance.
    """
    global _monitoring_logger
    if _monitoring_logger is None:
        _monitoring_logger = MonitoringLogger()
    return _monitoring_logger