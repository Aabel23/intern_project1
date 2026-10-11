"""The only place that opens a MySQL connection.

Every other module in database/ asks for a connection here and closes it
with close_database_resources().
"""

import mysql.connector

from database.core.config import DB_CONFIG, SERVER_CONFIG


def connect_server():
    """Connect to the MySQL server without selecting a database."""
    return mysql.connector.connect(**SERVER_CONFIG)


def connect_database():
    """Connect to the configured beverage database."""
    return mysql.connector.connect(**DB_CONFIG)


def close_database_resources(cursor=None, conn=None) -> None:
    """Close a cursor and a connection, ignoring the ones not given."""
    if cursor is not None:
        cursor.close()

    if conn is not None and conn.is_connected():
        conn.close()
