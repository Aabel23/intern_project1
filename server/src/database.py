"""One connection per transaction; never hold a DB transaction during SMTP."""
from contextlib import contextmanager
import mysql.connector
from server.src.types import ApiError, Settings

# Deadlock and lock-wait timeout roll back the whole transaction; the caller may retry it.
RETRYABLE_ERRNOS = {1205, 1213}
TRANSACTION_ATTEMPTS = 3


class RetryableTransaction(Exception):
    pass


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
    except mysql.connector.Error as error:
        if connection is not None:
            connection.rollback()
        if getattr(error, 'errno', None) in RETRYABLE_ERRNOS:
            raise RetryableTransaction() from None
        raise ApiError('SERVICE_UNAVAILABLE', 503) from None
    except Exception:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if connection is not None:
            connection.close()


def run_transaction(connect, work):
    """Run work(connection) in a fresh transaction, retrying deadlocks before reporting 503."""
    for _ in range(TRANSACTION_ATTEMPTS):
        try:
            with transaction(connect) as connection:
                return work(connection)
        except RetryableTransaction:
            continue
    raise ApiError('SERVICE_UNAVAILABLE', 503)
