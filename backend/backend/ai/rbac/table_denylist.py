"""
App-internal table denylist.

`DATABASE_URL` (business data) and `APP_DATABASE_URL` (this app's own
control-plane data) are two physically separate Postgres instances today,
so the NL-to-SQL pipeline can't reach these tables in practice - but that
separation is operational, not enforced in code. This denylist is
defense-in-depth: even if the two databases were ever consolidated onto
the same instance, generated SQL must never be allowed to touch tables
that belong to the app itself, only to the business data being analyzed.
"""

APP_INTERNAL_TABLES = frozenset({
    "users",
    "login_otp",
    "chat_sessions",
    "chat_messages",
    "user_notes",
    "query_logs",
    "system_prompts",
    "benchmark_questions",
    "eval_runs",
    "eval_results",
    "pipeline_eval_runs",
    "pipeline_eval_results",
    "admin_action_logs",
    "admin_audit_logs",
    "crud_confirm_tokens",
})
