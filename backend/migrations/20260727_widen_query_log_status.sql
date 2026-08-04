-- Allow every outcome the pipeline can produce to be logged.
--
-- Target: the APP control-plane database (APP_DATABASE_URL).
--
-- Why: `query_logs_status_check` permitted only 'success', 'rejected' and
-- 'error', but the code writes two more:
--   * 'clarification_needed'  - the pipeline asked the user a question back
--   * 'pending_confirmation'  - an admin write was proposed, awaiting confirm
--
-- Those INSERTs violated the constraint and failed. Logging is best-effort, so
-- the failure was swallowed as a warning and the row was simply lost. The
-- effect: every clarification and every proposed admin write was missing from
-- the audit trail, and the stored data showed only `success` and `error`.
--
-- Safe to re-run.

ALTER TABLE query_logs DROP CONSTRAINT IF EXISTS query_logs_status_check;

ALTER TABLE query_logs
    ADD CONSTRAINT query_logs_status_check
    CHECK (status IN (
        'success',
        'error',
        'rejected',
        'clarification_needed',
        'pending_confirmation'
    ));
