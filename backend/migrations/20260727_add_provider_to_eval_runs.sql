-- Record which model produced each benchmark run, and what it cost.
--
-- Target: the APP control-plane database (APP_DATABASE_URL).
--
-- Why: `eval_runs` stored an accuracy figure with no indication of which model
-- produced it. Every run so far was Groq (the default), so the stored history
-- silently mixes provider changes into one trend line and the app's own
-- Groq-vs-Gemini comparison could not be evaluated at all.
--
-- The usage columns make the comparison a real trade-off rather than a single
-- accuracy number: a model that is two points better but four times the cost is
-- a different decision.
--
-- All nullable, so the runs recorded before this migration stay valid - they
-- simply have no provider attributed. Safe to re-run.

ALTER TABLE eval_runs
    ADD COLUMN IF NOT EXISTS model_provider   text,
    ADD COLUMN IF NOT EXISTS model_name       text,
    ADD COLUMN IF NOT EXISTS input_tokens     bigint,
    ADD COLUMN IF NOT EXISTS output_tokens    bigint,
    ADD COLUMN IF NOT EXISTS estimated_cost   numeric(12, 8),
    ADD COLUMN IF NOT EXISTS avg_latency_ms   integer;

-- The comparison view reads the newest run per provider.
CREATE INDEX IF NOT EXISTS idx_eval_runs_provider_run_at
    ON eval_runs (model_provider, run_at DESC);
