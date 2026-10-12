"""Boot with provisioned environment; never migrate or manufacture runtime keys."""
from datetime import datetime, timezone
import logging
import time
from server.configuration.skeleton import load_settings
from server.src.crypto_keys import load_server_keys
from server.src.database import open_connection
from server.src.http import create_app
from server.src.smtp_mail import SMTPMail
from server.src.types import Dependencies, create_runtime_state


def main() -> None:
    server = None
    try:
        settings = load_settings()
        keys = load_server_keys(settings)
        deps = Dependencies(settings,lambda:open_connection(settings),lambda:datetime.now(timezone.utc),
                            time.monotonic,SMTPMail(settings),keys,create_runtime_state(settings))
        server = create_app(deps)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    except (ValueError, OSError):
        logging.getLogger(__name__).error('CONFIG_INVALID')
        raise SystemExit(1) from None
    finally:
        if server is not None: server.server_close()


if __name__ == '__main__':
    main()
