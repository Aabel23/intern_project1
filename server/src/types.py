"""Explicit runtime dependencies and wire results for skeleton account handlers."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable


class ApiError(Exception):
    def __init__(self, code: str, status: int, retry_after_seconds: int | None = None):
        super().__init__(code)
        self.code = code
        self.status = status
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str = field(repr=False)
    smtp_user: str
    smtp_from: str
    smtp_app_password: str = field(repr=False)
    otp_hash_secret: bytes = field(repr=False)
    server_bind_host: str
    server_bind_port: int
    tls_cert_file: str
    tls_key_file: str
    server_hpke_key_file: str
    server_signing_key_file: str
    server_trust_file: str
    app_env: str
    test_recipient_allowlist: tuple[str, ...]
    server_transport: str = 'https'


@dataclass(frozen=True)
class Dependencies:
    settings: Settings
    connect: Callable[[], Any] = field(repr=False)
    utc_now: Callable[[], datetime] = field(repr=False)
    monotonic: Callable[[], float] = field(repr=False)
    mail: Any = field(repr=False)
    keys: Any = field(repr=False)
    state: "RuntimeState" = field(repr=False)


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    session_id: str


@dataclass(frozen=True)
class RequestContext:
    ip: str
    auth: AuthContext | None = None
    machine: dict | None = None


@dataclass(frozen=True)
class HandlerResult:
    status: int
    payload: dict


@dataclass(frozen=True)
class OpenedRequest:
    body: dict = field(repr=False)
    auth: dict | None = field(repr=False)
    route: str
    send_id: str
    response_key: bytes = field(repr=False)
    machine: dict | None = None


@dataclass
class RuntimeState:
    guard: Any
    email_locks: dict
    rate_events: dict
    cooldown_until: dict
    replay_entries: dict
    http_slots: Any
    login_in_flight: dict = field(default_factory=dict)
    boot_wall_ms: int = 0
    poll_slots: Any = None
    relay_slots: Any = None
    relay: Any = None


def create_runtime_state(settings: Settings, boot_wall_ms: int = 0) -> RuntimeState:
    from threading import RLock, BoundedSemaphore
    from server.configuration import skeleton as cfg
    from server.src.relay import RelayHub
    return RuntimeState(RLock(), {}, {}, {}, {}, BoundedSemaphore(cfg.MAX_HTTP_REQUESTS), {}, boot_wall_ms,
                        BoundedSemaphore(cfg.MAX_POLL_REQUESTS), BoundedSemaphore(cfg.MAX_RELAY_REQUESTS), RelayHub())
