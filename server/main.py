"""Boot with provisioned environment; never migrate or manufacture runtime keys."""
from datetime import datetime, timezone
import logging
import time
from server.configuration.skeleton import load_local_environment, load_settings
from server.src.crypto_keys import load_server_keys
from server.src.database import open_connection
from server.src.http import create_app
from server.src.smtp_mail import SMTPMail
from server.src.types import Dependencies, create_runtime_state


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S')
    logger = logging.getLogger(__name__)
    server = None
    try:
        load_local_environment()
        settings = load_settings()
        keys = load_server_keys(settings)
        deps = Dependencies(settings,lambda:open_connection(settings),lambda:datetime.now(timezone.utc),
                            time.monotonic,SMTPMail(settings),keys,create_runtime_state(settings,int(time.time()*1000)))
        server = create_app(deps)
        logger.info('SERVER_READY https://%s:%s — Ctrl+C to stop', *server.server_address)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    except (ValueError, OSError):
        logging.getLogger(__name__).error('CONFIG_INVALID')
        raise SystemExit(1) from None
    finally:
        if server is not None:
            server.server_close()
            logger.info('SERVER_STOPPED')


if __name__ == '__main__':
    main()
