-- Add per-query LLM usage columns to `query_logs`.
--
-- Target: the APP control-plane database (APP_DATABASE_URL), not the business
-- database the chatbot queries.
--
-- Why: answering one question makes several LLM calls, and the token/cost/
-- latency figures were already computed in `LLMResponse` but thrown away
-- before reaching the database. Without these columns the app cannot report
-- what its own provider-comparison feature actually costs or how fast it is.
--
-- All columns are nullable so the rows written before this migration stay
-- valid; they simply have NULL usage. Safe to re-run.

ALTER TABLE query_logs
    ADD COLUMN IF NOT EXISTS model_provider  text,
    ADD COLUMN IF NOT EXISTS model_name      text,
    ADD COLUMN IF NOT EXISTS input_tokens    integer,
    ADD COLUMN IF NOT EXISTS output_tokens   integer,
    ADD COLUMN IF NOT EXISTS estimated_cost  numeric(12, 8),
    ADD COLUMN IF NOT EXISTS llm_latency_ms  integer;

-- Analytics group by provider over a time window; without this the dashboard
-- aggregations scan the whole table as it grows.
CREATE INDEX IF NOT EXISTS idx_query_logs_provider_created_at
    ON query_logs (model_provider, created_at DESC);
