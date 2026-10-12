"""One connection per transaction; never hold a DB transaction during SMTP."""
from contextlib import contextmanager
import mysql.connector
from server.src.types import ApiError, Settings


def open_connection(settings: Settings):
    return mysql.connector.connect(
        host=settings.db_host, port=settings.db_port, database=settings.db_name,
        user=settings.db_user, password=settings.db_password, autocommit=False,
        time_zone='+00:00',
    )


@contextmanager
def transaction(connect):
    connection = None
    try:
        connection = connect()
        yield connection
        connection.commit()
    except mysql.connector.Error:
        if connection is not None:
            connection.rollback()
        raise ApiError('SERVICE_UNAVAILABLE', 503) from None
    except Exception:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if connection is not None:
            connection.close()
