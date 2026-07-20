"""
Clarification Prompt Module.

Handles detection and generation of clarifying questions when user input is ambiguous.
Prevents invalid SQL generation by asking for clarification upfront.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class AmbiguityType(Enum):
    """
    Enumeration of ambiguity types that require clarification.
    """
    TIME_PERIOD = "time_period"  # e.g., "sales" without specifying today/month/year
    ENTITY_SELECTION = "entity_selection"  # e.g., "customer" without specifying which
    AGGREGATION_TYPE = "aggregation_type"  # e.g., "total" without specifying sum/count
    DATE_RANGE = "date_range"  # e.g., "last period" needs clarification
    COLUMN_AMBIGUITY = "column_ambiguity"  # Multiple columns match the description
    METRIC_AMBIGUITY = "metric_ambiguity"  # e.g., "revenue" could be from different sources
    COMPARISON_PERIOD = "comparison_period"  # e.g., "compare" without specifying to what
    UNKNOWN = "unknown"  # Generic ambiguity


@dataclass
class ClarificationQuestion:
    """
    Represents a clarification question to ask the user.
    
    Attributes:
        question: The clarification question text
        ambiguity_type: Type of ambiguity detected
        options: List of possible options/answers
        is_required: Whether clarification is mandatory
        confidence_score: Confidence that clarification is needed (0-1)
    """
    question: str
    ambiguity_type: AmbiguityType
    options: List[str]
    is_required: bool = True
    confidence_score: float = 0.8


class ClarificationPromptManager:
    """
    Manages clarification prompt generation and ambiguity detection.
    
    Responsible for:
    - Detecting ambiguous user questions
    - Generating clarifying questions
    - Providing structured options for the user
    - Tracking clarification history
    """

    # ============ Ambiguity Detection System Prompt ============
    DETECTION_SYSTEM_PROMPT = """You are an expert at detecting ambiguous or unclear requests in natural language.

Your task is to analyze a user question and determine if it needs clarification before SQL can be generated.

## AMBIGUITY TYPES TO DETECT:

1. **TIME_PERIOD**: Question mentions a metric without specifying when (e.g., "Show sales" without today/week/month/year)
2. **ENTITY_SELECTION**: Question refers to an entity without specifying which one (e.g., "Show customer purchases" without naming a customer)
3. **AGGREGATION_TYPE**: Question is vague about how to aggregate (e.g., "Total revenue" could mean SUM or COUNT)
4. **DATE_RANGE**: Question uses relative dates that need clarification (e.g., "recent", "last period")
5. **COLUMN_AMBIGUITY**: Multiple columns could match the description (e.g., "price" could be unit_price or total_price)
6. **METRIC_AMBIGUITY**: A metric name is ambiguous (e.g., "revenue" from sales or refunds)
7. **COMPARISON_PERIOD**: Comparison lacks specification (e.g., "Compare sales" without comparing to what/when)

## YOUR RESPONSE FORMAT:

Return a JSON object with this structure:
{
    "is_ambiguous": boolean,
    "confidence_score": float (0-1),
    "ambiguity_type": string (one of the types above, or "unknown"),
    "explanation": string (why it's ambiguous),
    "clarification_needed": string (what needs to be clarified)
}

If the question is clear and unambiguous, return:
{
    "is_ambiguous": false,
    "confidence_score": 1.0,
    "ambiguity_type": "unknown",
    "explanation": "Question is clear",
    "clarification_needed": null
}

Be conservative: Only flag as ambiguous if there's genuine uncertainty."""

    # ============ Clarification Generation Prompt ============
    GENERATION_SYSTEM_PROMPT = """You are an expert at generating helpful clarification questions.

Given an ambiguous user question and the type of ambiguity, generate 3-4 specific options that the user can choose from.

## RULES:

1. Make options mutually exclusive
2. Cover the most common/likely scenarios
3. Be specific and actionable
4. Use simple, clear language
5. If applicable, provide default recommendation

## OUTPUT FORMAT:

Return a JSON object:
{
    "question": "Clarifying question text",
    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
    "recommended": "Index of recommended option (0-based)",
    "follow_up": "Optional follow-up question after this one"
}"""

    # ============ Predefined Clarifications ============
    CLARIFICATIONS_LIBRARY = {
        AmbiguityType.TIME_PERIOD: {
            "question": "Which time period would you like to analyze?",
            "options": [
                "Today",
                "This week",
                "This month",
                "This year",
                "Last 7 days",
                "Last 30 days"
            ],
            "recommended": 2  # "This month" is most common default
        },
        AmbiguityType.ENTITY_SELECTION: {
            "question": "Which specific item would you like to analyze?",
            "options": [
                "Show me available options",
                "Most recent",
                "Highest value",
                "All items"
            ],
            "recommended": 0
        },
        AmbiguityType.DATE_RANGE: {
            "question": "Please specify the date range:",
            "options": [
                "Last 7 days",
                "Last 30 days",
                "This month",
                "Last month",
                "Custom date range"
            ],
            "recommended": 1  # "Last 30 days" is common default
        },
        AmbiguityType.AGGREGATION_TYPE: {
            "question": "How would you like to aggregate the data?",
            "options": [
                "Sum (total)",
                "Count (number of records)",
                "Average",
                "Maximum",
                "Minimum"
            ],
            "recommended": 0  # "Sum" is most common
        },
        AmbiguityType.METRIC_AMBIGUITY: {
            "question": "Which metric do you want to see?",
            "options": [
                "Show me available metrics",
                "Primary metric",
                "All metrics"
            ],
            "recommended": 0
        },
        AmbiguityType.COLUMN_AMBIGUITY: {
            "question": "Which column did you mean?",
            "options": [
                "Show me available columns",
                "Most common option",
                "Show all matching columns"
            ],
            "recommended": 0
        },
        AmbiguityType.COMPARISON_PERIOD: {
            "question": "What would you like to compare this to?",
            "options": [
                "Previous period",
                "Previous year",
                "Custom period",
                "All available periods"
            ],
            "recommended": 0
        }
    }

    def __init__(self):
        """Initialize the Clarification Prompt Manager."""
        pass

    def detect_ambiguity(
        self,
        user_question: str,
        available_context: Optional[Dict] = None
    ) -> Dict:
        """
        Detect if a user question is ambiguous.
        
        Args:
            user_question (str): The user's natural language question.
            available_context (Optional[Dict]): Additional context (schema, available tables, etc.).
        
        Returns:
            Dict: Ambiguity analysis with detection result.
        """
        import logging
        logger = logging.getLogger(__name__)

        question_lower = user_question.lower().strip()

        # Immediate bypass for clear read operations and general listing commands
        clear_read_indicators = [
            "show all", "list all", "display all", "get all", "select all",
            "how many", "count", "total", "sum", "average", "avg", "mean",
            "max", "min", "highest", "lowest", "top ", "bottom ",
            "breakdown", "group by", "catalog", "logs", "activity", "benchmark",
            "show products", "list products", "show customers", "list customers",
            "show orders", "list orders", "show payments", "list payments",
            "show users", "list users", "show categories", "list categories",
            "show table", "list table", "show database", "show schema"
        ]
        if any(indicator in question_lower for indicator in clear_read_indicators):
            return {
                "is_ambiguous": False,
                "confidence_score": 1.0,
                "ambiguity_type": AmbiguityType.UNKNOWN,
                "explanation": "Question is a clear read/aggregation command, bypassing ambiguity check.",
                "clarification_needed": None
            }

        # Pattern-based ambiguity detection (fast-track)
        pattern_result = self._check_ambiguity_patterns(user_question)
        if pattern_result["is_ambiguous"]:
            return pattern_result
        
        # Second pass: LLM semantic ambiguity check
        try:
            from backend.ai.llm.client import get_llm_client
            llm_client = get_llm_client()
            
            # Format prompt with user question
            response = llm_client.generate_json(
                system_prompt=self.DETECTION_SYSTEM_PROMPT,
                user_prompt=f"Analyze this question: {user_question}"
            )
            
            is_ambiguous = bool(response.get("is_ambiguous"))
            if is_ambiguous:
                # Resolve ambiguity type string to AmbiguityType enum
                amb_type_str = str(response.get("ambiguity_type", "unknown")).lower()
                ambiguity_type = AmbiguityType.UNKNOWN
                for t in AmbiguityType:
                    if t.value == amb_type_str:
                        ambiguity_type = t
                        break
                        
                return {
                    "is_ambiguous": True,
                    "confidence_score": float(response.get("confidence_score", 0.8)),
                    "ambiguity_type": ambiguity_type,
                    "explanation": str(response.get("explanation", "Ambiguity detected")),
                    "clarification_needed": response.get("clarification_needed")
                }
        except Exception as e:
            logger.warning(f"LLM ambiguity detection failed, falling back: {str(e)}")

        # If no pattern matches and LLM didn't flag it, return clear
        return {
            "is_ambiguous": False,
            "confidence_score": 1.0,
            "ambiguity_type": AmbiguityType.UNKNOWN,
            "explanation": "Question is clear and unambiguous",
            "clarification_needed": None
        }

    def _check_ambiguity_patterns(self, user_question: str) -> Dict:
        """
        Check for common ambiguity patterns.
        
        Args:
            user_question (str): The user question to analyze.
        
        Returns:
            Dict: Pattern-based ambiguity detection result.
        """
        question_lower = user_question.lower()
        
        # Aggregate/ranking/listing questions ("how many customers", "total
        # revenue by category", "list all products") ask about the whole
        # set - either all-time or the whole entity - not one unspecified
        # instance or an implied-but-missing date range.
        aggregate_indicators = [
            "how many", "count", "total", "sum", "average", "avg",
            "all ", "list", "each ", "every ", "number of",
            "top ", "highest", "lowest", "most", "least", "by category",
            "by region", "by department", "group by", "per "
        ]

        # ============ Time Period Ambiguity ============
        if any(word in question_lower for word in ["show", "display", "get", "sales", "revenue", "orders"]):
            if not any(word in question_lower for word in
                      ["today", "this week", "this month", "this year", "last 7", "last 30",
                       "yesterday", "january", "february", "march", "april", "may", "june",
                       "july", "august", "september", "october", "november", "december",
                       "2024", "2025"]):
                if any(word in question_lower for word in ["sales", "revenue", "orders", "purchases"]):
                    if not any(word in question_lower for word in aggregate_indicators):
                        return {
                            "is_ambiguous": True,
                            "confidence_score": 0.85,
                            "ambiguity_type": AmbiguityType.TIME_PERIOD,
                            "explanation": "Question mentions a metric but doesn't specify the time period",
                            "clarification_needed": "Which time period?"
                        }

        # ============ Date Range Ambiguity ============
        # Distinct from TIME_PERIOD above: this catches a relative-date
        # phrase ("recent", "last period") standing in for a real range,
        # rather than a metric with no time reference at all.
        relative_date_phrases = ["recent", "recently", "last few", "past few", "lately", "last period"]
        if any(phrase in question_lower for phrase in relative_date_phrases):
            if not any(word in question_lower for word in
                      ["today", "this week", "this month", "this year", "last 7", "last 30",
                       "yesterday", "january", "february", "march", "april", "may", "june",
                       "july", "august", "september", "october", "november", "december",
                       "2024", "2025"]):
                return {
                    "is_ambiguous": True,
                    "confidence_score": 0.75,
                    "ambiguity_type": AmbiguityType.DATE_RANGE,
                    "explanation": "Question uses a relative date phrase without a specific range",
                    "clarification_needed": "Which date range?"
                }

        # ============ Entity Selection Ambiguity ============
        if any(word in question_lower for word in ["customer", "product", "category", "region", "department"]):
            if not any(word in question_lower for word in aggregate_indicators):
                if "which" not in question_lower and "the" not in question_lower:
                    if not any(char.isdigit() for char in question_lower):  # No ID specified
                        return {
                            "is_ambiguous": True,
                            "confidence_score": 0.80,
                            "ambiguity_type": AmbiguityType.ENTITY_SELECTION,
                            "explanation": "Question references an entity but doesn't specify which one",
                            "clarification_needed": "Which specific entity?"
                        }
        
        # ============ Comparison Ambiguity ============
        if any(word in question_lower for word in ["compare", "versus", "vs", "difference", "against"]):
            if question_lower.count("between") < 2 and not any(word in question_lower for word in 
                                                               ["january", "february", "march", "april", 
                                                                "may", "june", "july", "august", 
                                                                "september", "october", "november", "december"]):
                return {
                    "is_ambiguous": True,
                    "confidence_score": 0.75,
                    "ambiguity_type": AmbiguityType.COMPARISON_PERIOD,
                    "explanation": "Comparison question doesn't clearly specify what to compare with",
                    "clarification_needed": "Compare to what/which period?"
                }
        
        # ============ No Ambiguity Detected ============
        return {
            "is_ambiguous": False,
            "confidence_score": 1.0,
            "ambiguity_type": AmbiguityType.UNKNOWN,
            "explanation": "Question is clear",
            "clarification_needed": None
        }

    def generate_clarification_question(
        self,
        ambiguity_type: AmbiguityType
    ) -> ClarificationQuestion:
        """
        Generate a clarification question for a specific ambiguity type.
        
        Args:
            ambiguity_type (AmbiguityType): The type of ambiguity detected.
        
        Returns:
            ClarificationQuestion: A structured clarification question.
            
        Example:
            clarification = manager.generate_clarification_question(
            AmbiguityType.TIME_PERIOD
        )
        # Returns: ClarificationQuestion with question and options
        """
        if ambiguity_type not in self.CLARIFICATIONS_LIBRARY:
            # Fallback for unknown ambiguity types
            return ClarificationQuestion(
                question="Could you provide more details about your question?",
                ambiguity_type=AmbiguityType.UNKNOWN,
                options=["Show me available options", "Let me rephrase"],
                is_required=True,
                confidence_score=0.6
            )
        
        clarif = self.CLARIFICATIONS_LIBRARY[ambiguity_type]
        
        return ClarificationQuestion(
            question=clarif["question"],
            ambiguity_type=ambiguity_type,
            options=clarif["options"],
            is_required=True,
            confidence_score=0.8
        )

    def build_clarification_prompt(self, user_question: str) -> Dict[str, str]:
        """
        Build a complete clarification prompt response.
        
        Args:
            user_question (str): The user's question.
        
        Returns:
            Dict[str, str]: The formatted clarification response for the user.
        """
        ambiguity_analysis = self.detect_ambiguity(user_question)
        
        if not ambiguity_analysis["is_ambiguous"]:
            return {
                "status": "clear",
                "is_ambiguous": False,
                "message": "Your question is clear. Proceeding to SQL generation."
            }
        
        ambiguity_type = ambiguity_analysis["ambiguity_type"]
        clarification = self.generate_clarification_question(ambiguity_type)
        
        return {
            "status": "clarification_needed",
            "is_ambiguous": True,
            "ambiguity_type": ambiguity_type.value,
            "confidence_score": ambiguity_analysis["confidence_score"],
            "question": clarification.question,
            "options": clarification.options,
            "explanation": ambiguity_analysis["explanation"],
            "user_original_question": user_question
        }

    def merge_clarification_with_question(
        self,
        original_question: str,
        clarification_answer: str
    ) -> str:
        """
        Merge user's clarification answer with original question.
        
        This creates a more specific question for SQL generation.
        
        Args:
            original_question (str): The original user question.
            clarification_answer (str): The user's answer to clarification.
        
        Returns:
            str: A more specific, non-ambiguous question.
        """
        ans_lower = clarification_answer.lower().strip()
        orig_lower = original_question.lower().strip()

        # Handle ENTITY_SELECTION clarification options
        if "show me available options" in ans_lower or "all items" in ans_lower:
            noun = orig_lower
            if not noun.endswith('s') and noun in ['product', 'customer', 'order', 'category', 'item']:
                noun = noun + 's'
            return f"show all {noun}"
        
        if "most recent" in ans_lower:
            noun = orig_lower
            if not noun.endswith('s') and noun in ['product', 'customer', 'order', 'category', 'item']:
                noun = noun + 's'
            return f"show the most recent {noun}"
            
        if "highest value" in ans_lower:
            noun = orig_lower
            if not noun.endswith('s') and noun in ['product', 'customer', 'order', 'category', 'item']:
                noun = noun + 's'
            return f"show the {noun} with the highest price or value"

        # Handle other types of generic "show me available..." responses
        if "show me available" in ans_lower:
            return f"list all available items for {orig_lower}"

        # Standard merge
        return f"{original_question} for {clarification_answer.lower()}"

    def is_ambiguity_threshold_exceeded(
        self,
        confidence_score: float,
        threshold: float = 0.6
    ) -> bool:
        """
        Check if ambiguity confidence exceeds threshold.
        
        Args:
            confidence_score (float): The confidence score (0-1).
            threshold (float): The threshold for clarification (default: 0.6).
        
        Returns:
            bool: True if ambiguity is above threshold.
        """
        return confidence_score >= threshold

    def format_clarification_response(
        self,
        clarification_question: ClarificationQuestion
    ) -> Dict:
        """
        Format clarification question for API response.
        
        Args:
            clarification_question (ClarificationQuestion): The clarification object.
        
        Returns:
            Dict: Formatted response for frontend.
        """
        return {
            "type": "clarification",
            "question": clarification_question.question,
            "options": clarification_question.options,
            "ambiguity_type": clarification_question.ambiguity_type.value,
            "is_required": clarification_question.is_required,
            "confidence_score": clarification_question.confidence_score
        }


# ============ Singleton Instance ============
clarification_prompt_manager = ClarificationPromptManager()


def get_clarification_prompt_manager() -> ClarificationPromptManager:
    """
    Get the global Clarification Prompt Manager instance.
    
    Returns:
        ClarificationPromptManager: The prompt manager instance.
    """
    return clarification_prompt_manager