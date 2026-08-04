"""
Unit tests for LLM usage accounting.

Pure-function tests, no database/LLM dependency - covers the two pieces the
per-query cost/token reporting depends on: summing usage across the several
LLM calls one question makes (`aggregate_llm_usage`), and pricing lookup
(`TokenCounter.estimate_cost`), including the unknown-model case that must
report zero *loudly* rather than silently.
"""

import logging

from backend.ai.llm.client import TokenCounter
from backend.ai.llm.generator import aggregate_llm_usage


def _response(model="llama-3.1-8b-instant", input_tokens=100, output_tokens=20,
              cost=0.001, latency=500.0):
    """Shape of LLMResponse.to_dict(), which is what the generators store."""
    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "estimated_cost": cost,
        "latency_ms": latency,
    }


class TestAggregateLLMUsage:
    """Tests for `aggregate_llm_usage`."""

    def test_sums_across_calls(self):
        """One question = SQL + explanation + chart calls; totals are what matter."""
        result = aggregate_llm_usage(
            _response(input_tokens=1000, output_tokens=50, cost=0.002, latency=900.0),
            _response(input_tokens=300, output_tokens=80, cost=0.001, latency=400.0),
            _response(input_tokens=200, output_tokens=30, cost=0.0005, latency=300.0),
        )

        assert result["llm_calls"] == 3
        assert result["input_tokens"] == 1500
        assert result["output_tokens"] == 160
        assert result["total_tokens"] == 1660
        assert result["estimated_cost"] == 0.0035
        assert result["llm_latency_ms"] == 1600.0

    def test_skips_calls_that_did_not_happen(self):
        """A step that fell back to a non-LLM path contributes None, not zeros."""
        result = aggregate_llm_usage(_response(), None, None)

        assert result["llm_calls"] == 1
        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 20

    def test_no_calls_at_all(self):
        """Paths that never touch an LLM produce a well-formed empty total."""
        result = aggregate_llm_usage(None, None, None)

        assert result["llm_calls"] == 0
        assert result["model_name"] is None
        assert result["total_tokens"] == 0
        assert result["estimated_cost"] == 0.0

    def test_model_name_taken_from_first_real_call(self):
        result = aggregate_llm_usage(None, _response(model="gemini-flash-lite-latest"))

        assert result["model_name"] == "gemini-flash-lite-latest"

    def test_missing_fields_treated_as_zero(self):
        """A malformed/partial response dict must not blow up the totals."""
        result = aggregate_llm_usage({"model": "x"}, _response(input_tokens=10, output_tokens=5))

        assert result["llm_calls"] == 2
        assert result["input_tokens"] == 10
        assert result["output_tokens"] == 5

    def test_none_valued_fields_treated_as_zero(self):
        """Explicit None values (not just absent keys) must also be safe."""
        partial = {"model": "x", "input_tokens": None, "output_tokens": None,
                   "estimated_cost": None, "latency_ms": None}
        result = aggregate_llm_usage(partial)

        assert result["input_tokens"] == 0
        assert result["estimated_cost"] == 0.0
        assert result["llm_latency_ms"] == 0.0


class TestEstimateCost:
    """Tests for `TokenCounter.estimate_cost`."""

    def test_known_groq_model_costs_more_than_zero(self):
        cost = TokenCounter.estimate_cost("llama-3.1-8b-instant", 1000, 1000)

        assert cost > 0

    def test_known_gemini_model_is_priced(self):
        """Gemini was missing from the table, so its cost silently read $0.00."""
        cost = TokenCounter.estimate_cost("gemini-flash-lite-latest", 1000, 1000)

        assert cost > 0

    def test_cost_scales_with_tokens(self):
        small = TokenCounter.estimate_cost("llama-3.1-8b-instant", 1000, 1000)
        large = TokenCounter.estimate_cost("llama-3.1-8b-instant", 10_000, 10_000)

        assert large > small

    def test_unknown_model_returns_zero_and_warns(self, caplog):
        """Silent zeros become fake numbers in a report - it must warn."""
        with caplog.at_level(logging.WARNING):
            cost = TokenCounter.estimate_cost("some-model-we-never-priced", 1000, 1000)

        assert cost == 0.0
        assert "No pricing entry" in caplog.text
