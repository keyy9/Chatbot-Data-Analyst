"""
Unit tests for database-error explanations.

Pure functions - no database.

These cover the message an admin actually saw when deleting a product that is
still on existing orders: raw psycopg2 output about
`order_items_product_id_fkey`, with no indication of what to do next.
"""

from backend.api.services.db_errors import explain_database_error

FK_ERROR = (
    'update or delete on table "products" violates foreign key constraint '
    '"order_items_product_id_fkey" on table "order_items"\n'
    'DETAIL:  Key (product_id)=(1) is still referenced from table "order_items".'
)


class TestForeignKey:
    def test_names_the_table_that_blocks_the_delete(self):
        message = explain_database_error(Exception(FK_ERROR))

        assert "order_items" in message

    def test_names_the_key_that_is_still_referenced(self):
        message = explain_database_error(Exception(FK_ERROR))

        assert "product_id" in message
        assert "1" in message

    def test_describes_the_row_in_singular(self):
        """"This product is still in use", not "This products"."""
        message = explain_database_error(Exception(FK_ERROR))

        assert "product is still in use" in message

    def test_says_what_the_admin_can_do(self):
        message = explain_database_error(Exception(FK_ERROR))

        assert "reassign" in message or "remove" in message

    def test_states_that_nothing_changed(self):
        """A failed write must not leave the admin guessing about the data."""
        message = explain_database_error(Exception(FK_ERROR))

        assert "Nothing was changed" in message

    def test_drops_the_raw_constraint_jargon(self):
        message = explain_database_error(Exception(FK_ERROR))

        assert "violates foreign key constraint" not in message
        assert "DETAIL:" not in message


class TestOtherIntegrityFailures:
    def test_not_null_names_the_column(self):
        message = explain_database_error(Exception(
            'null value in column "product_name" of relation "products" '
            'violates not-null constraint'
        ))

        assert "product_name" in message
        assert "cannot be empty" in message

    def test_unique_violation_names_the_clashing_value(self):
        message = explain_database_error(Exception(
            'duplicate key value violates unique constraint "users_email_key"\n'
            'DETAIL:  Key (email)=(someone@example.com) already exists.'
        ))

        assert "someone@example.com" in message
        assert "already exists" in message

    def test_check_violation_names_the_constraint(self):
        message = explain_database_error(Exception(
            'new row for relation "query_logs" violates check constraint '
            '"query_logs_status_check"'
        ))

        assert "query_logs_status_check" in message


class TestUnrecognisedErrors:
    def test_unknown_error_returns_none(self):
        """The caller must fall back to the original message, not invent one."""
        assert explain_database_error(Exception("connection reset by peer")) is None

    def test_empty_error_returns_none(self):
        assert explain_database_error(Exception("")) is None


class TestSingularisation:
    def test_plural_table_names_read_naturally(self):
        from backend.api.services.db_errors import _singular

        assert _singular("products") == "product"
        assert _singular("categories") == "category"
        assert _singular("addresses") == "address"
        assert _singular("data") == "data"
