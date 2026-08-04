"""
Turn database integrity errors into something an admin can act on.

Postgres refuses writes that would break the schema's own rules, and the raw
message it returns is precise but unreadable:

    update or delete on table "products" violates foreign key constraint
    "order_items_product_id_fkey" on table "order_items"
    DETAIL:  Key (product_id)=(1) is still referenced from table "order_items".

That was being passed straight to the chat window. It names the real problem -
the product is still on existing orders - but an admin has to know how to read
it, and it says nothing about what to do next.

These are refusals worth keeping. Cascading the delete automatically would
erase order history to satisfy a request to remove one product, so the fix is
to explain the block, not to remove it.

Pure functions: no I/O, so the wording can be tested directly.
"""

import re
from typing import Optional

# "Key (product_id)=(1) is still referenced from table "order_items"."
_FK_DETAIL = re.compile(
    r'Key \((?P<column>[^)]+)\)=\((?P<value>[^)]*)\) is still referenced from table "(?P<child>[^"]+)"',
    re.IGNORECASE,
)
_FK_HEADLINE = re.compile(
    r'(?:update or delete )?on table "(?P<parent>[^"]+)" violates foreign key constraint',
    re.IGNORECASE,
)
_NOT_NULL = re.compile(
    r'null value in column "(?P<column>[^"]+)"(?: of relation "(?P<table>[^"]+)")?',
    re.IGNORECASE,
)
_UNIQUE_DETAIL = re.compile(
    r'Key \((?P<column>[^)]+)\)=\((?P<value>[^)]*)\) already exists',
    re.IGNORECASE,
)
_CHECK = re.compile(
    r'violates check constraint "(?P<constraint>[^"]+)"',
    re.IGNORECASE,
)


def explain_database_error(error: Exception) -> Optional[str]:
    """
    Describe a database refusal in plain language, with the way forward.

    Args:
        error: The exception raised while executing the statement.

    Returns:
        Optional[str]: A readable explanation, or None when the error is not
            one of the recognised integrity failures - in that case the caller
            should surface the original message rather than invent one.
    """
    raw = " ".join(str(error).split())

    fk_detail = _FK_DETAIL.search(raw)
    if fk_detail:
        child = fk_detail.group("child")
        column = fk_detail.group("column")
        value = fk_detail.group("value")
        parent_match = _FK_HEADLINE.search(raw)
        parent = parent_match.group("parent") if parent_match else "this record"

        return (
            f"This {_singular(parent)} is still in use, so the database refused to remove it. "
            f"Rows in \"{child}\" still point at {column} = {value} - deleting it would leave "
            f"those rows referring to something that no longer exists.\n\n"
            f"You can either remove or reassign the matching rows in \"{child}\" first, "
            f"or leave this {_singular(parent)} in place. Nothing was changed."
        )

    not_null = _NOT_NULL.search(raw)
    if not_null:
        column = not_null.group("column")
        table = not_null.group("table")
        where = f' in "{table}"' if table else ""
        return (
            f'The column "{column}"{where} cannot be empty, and no value was supplied for it. '
            f"Include a value for it and try again. Nothing was changed."
        )

    unique = _UNIQUE_DETAIL.search(raw)
    if unique:
        column = unique.group("column")
        value = unique.group("value")
        return (
            f"A record with {column} = {value} already exists, and that column has to be "
            f"unique. Use a different value, or update the existing record instead. "
            f"Nothing was changed."
        )

    check = _CHECK.search(raw)
    if check:
        return (
            f"The value breaks a rule the database enforces on this table "
            f"(constraint \"{check.group('constraint')}\"). Check the allowed values for the "
            f"columns you are setting. Nothing was changed."
        )

    return None


def _singular(table_name: str) -> str:
    """Read a table name as one row of it: 'products' -> 'product'."""
    name = table_name.rstrip()
    if name.endswith("ies"):
        return name[:-3] + "y"
    if name.endswith("ses"):
        return name[:-2]
    if name.endswith("s") and not name.endswith("ss"):
        return name[:-1]
    return name
