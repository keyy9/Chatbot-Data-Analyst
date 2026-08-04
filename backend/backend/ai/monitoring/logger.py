"""
Event logging for the request pipeline.

Emits structured one-line records through Python's standard logging so the
pipeline's decisions (SQL generated, statement executed, request rejected)
show up in the server log next to everything else.

Scope note: this module deliberately does NOT keep metrics. It used to hold
an in-memory event store plus token/cost accounting that nothing ever read -
metrics that need to survive a restart belong in a table. Durable per-query
usage (provider, model, tokens, cost, latency) is written to `query_logs` by
`backend.ai.monitoring.query_log_repository`, and aggregated for the
dashboard by the admin analytics endpoints.
"""

import logging
from enum import Enum
from typing import Dict, Optional

# ============ Setup Logging ============
logger = logging.getLogger(__name__)


class EventType(Enum):
    """Enumeration of monitored event types."""
    SQL_GENERATION = "sql_generation"
    SQL_VALIDATION = "sql_validation"
    SQL_EXECUTION = "sql_execution"
    EXPLANATION_GENERATION = "explanation_generation"
    CHART_RECOMMENDATION = "chart_recommendation"
    CLARIFICATION_REQUEST = "clarification_request"
    API_CALL = "api_call"
    ERROR = "error"
    WARNING = "warning"


class MonitoringLogger:
    """Emits pipeline events to the standard logger."""

    def log_event(
        self,
        event_type: EventType,
        message: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        duration_ms: float = 0.0,
        status: str = "success",
        error: Optional[str] = None,
        metadata: Optional[Dict] = None,
        **kwargs
    ) -> None:
        """
        Log one pipeline event.

        Args:
            event_type: Type of event.
            message: Event message.
            user_id: User identifier.
            session_id: Session identifier.
            duration_ms: Duration in milliseconds.
            status: Status (success/failure/partial).
            error: Error message, if applicable.
            metadata: Additional context to include in the line.
            **kwargs: Extra fields; accepted and appended so callers can pass
                context without this signature having to know about it.
        """
        parts = [f"[{event_type.value}] {message}"]
        if user_id:
            parts.append(f"user={user_id}")
        if session_id:
            parts.append(f"session={session_id}")
        parts.append(f"status={status}")
        if duration_ms:
            parts.append(f"duration={duration_ms:.0f}ms")
        if error:
            parts.append(f"error={error}")
        if metadata:
            parts.append(f"metadata={metadata}")
        if kwargs:
            parts.append(f"extra={kwargs}")

        line = " ".join(parts)

        if status == "failure" or event_type is EventType.ERROR:
            logger.error(line)
        elif status == "warning" or event_type is EventType.WARNING:
            logger.warning(line)
        else:
            logger.info(line)

    def log_error(
        self,
        user_id: Optional[str],
        session_id: Optional[str],
        error_message: str,
        error_type: str,
        component: str,
        duration_ms: float = 0.0,
        metadata: Optional[Dict] = None
    ) -> None:
        """Log a failure, naming the component it came from."""
        self.log_event(
            event_type=EventType.ERROR,
            message=f"Error in {component}: {error_message}",
            user_id=user_id,
            session_id=session_id,
            duration_ms=duration_ms,
            status="failure",
            error=error_message,
            metadata={**(metadata or {}), "error_type": error_type},
        )


# ============ Singleton Instance ============
_monitoring_logger: Optional[MonitoringLogger] = None


def get_monitoring_logger() -> MonitoringLogger:
    """Get or create the global monitoring logger."""
    global _monitoring_logger

    if _monitoring_logger is None:
        _monitoring_logger = MonitoringLogger()

    return _monitoring_logger
