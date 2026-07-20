"""
AI/LLM Core Module for Conversational Data Analyst.

Exposes main components and utilities.
"""

from backend.ai.config import get_settings, validate_config, is_production, is_development
from backend.ai.llm.client import LLMClient, AsyncLLMClient, get_llm_client, get_async_llm_client
from backend.ai.llm.generator import (
    SQLGenerator,
    ExplanationGenerator,
    ChartRecommender,
    PipelineOrchestrator,
    SQLGenerationResult,
    ExplanationResult,
    ChartRecommendationResult,
    get_sql_generator,
    get_explanation_generator,
    get_chart_recommender,
    get_pipeline_orchestrator
)
from backend.ai.validators.sql_guard import SQLGuardValidator, get_sql_guard_validator
from backend.ai.prompts.sql_prompt import SQLPromptManager, get_sql_prompt_manager
from backend.ai.prompts.clarification_prompt import (
    ClarificationPromptManager,
    get_clarification_prompt_manager
)
from backend.ai.prompts.explanation_prompt import (
    ExplanationPromptManager,
    get_explanation_prompt_manager
)
from backend.ai.prompts.chart_prompt import ChartPromptManager, get_chart_prompt_manager
from backend.ai.explanation.explainer import (
    ExplanationBuilder,
    InsightExtractor,
    ResultFormatter,
    SourceAttributor,
    get_explanation_builder,
    get_source_attributor
)
from backend.ai.evaluation.evaluator import (
    ModelEvaluator,
    EvaluationResult,
    get_model_evaluator
)
from backend.ai.monitoring.logger import (
    MonitoringLogger,
    MonitoringEvent,
    EventType,
    EventSeverity,
    get_monitoring_logger
)

__version__ = "1.0.0"
__author__ = "AI Team"

__all__ = [
    # Config
    "get_settings",
    "validate_config",
    "is_production",
    "is_development",
    
    # LLM Client
    "LLMClient",
    "AsyncLLMClient",
    "get_llm_client",
    "get_async_llm_client",
    
    # Generators
    "SQLGenerator",
    "ExplanationGenerator",
    "ChartRecommender",
    "PipelineOrchestrator",
    "SQLGenerationResult",
    "ExplanationResult",
    "ChartRecommendationResult",
    "get_sql_generator",
    "get_explanation_generator",
    "get_chart_recommender",
    "get_pipeline_orchestrator",
    
    # Validators
    "SQLGuardValidator",
    "get_sql_guard_validator",
    
    # Prompts
    "SQLPromptManager",
    "get_sql_prompt_manager",
    "ClarificationPromptManager",
    "get_clarification_prompt_manager",
    "ExplanationPromptManager",
    "get_explanation_prompt_manager",
    "ChartPromptManager",
    "get_chart_prompt_manager",
    
    # Explanation
    "ExplanationBuilder",
    "InsightExtractor",
    "ResultFormatter",
    "SourceAttributor",
    "get_explanation_builder",
    "get_source_attributor",
    
    # Evaluation
    "ModelEvaluator",
    "EvaluationResult",
    "get_model_evaluator",
    
    # Monitoring
    "MonitoringLogger",
    "MonitoringEvent",
    "EventType",
    "EventSeverity",
    "get_monitoring_logger",
]


def initialize_ai_core():
    """
    Initialize the AI core module.
    
    Validates configuration and initializes all components.
    
    Returns:
        bool: True if initialization successful.
        
    Raises:
        ValueError: If configuration is invalid.
    """
    try:
        # Validate config
        validate_config()
        
        # Initialize main components
        get_sql_generator()
        get_explanation_generator()
        get_chart_recommender()
        get_pipeline_orchestrator()
        get_model_evaluator()
        get_monitoring_logger()
        
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to initialize AI core: {str(e)}")