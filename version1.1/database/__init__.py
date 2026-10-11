"""FlexMix database package.

    core/       config, MySQL connection, shared helpers
    schema/     schema.sql + seed.sql and the code that applies them
    services/   one module per business area: inventory, order_ticket,
                error_log, recipe_export
"""

from database.schema.apply import apply_database_sql
from database.services.inventory import check_inventory

__all__ = [
    "apply_database_sql",
    "check_inventory",
]
