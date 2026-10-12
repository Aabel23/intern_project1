"""HTTPS stdlib entry point; business messages are always inside HPKE envelopes."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import logging
import ssl
from server.configuration import routing, skeleton as cfg
from server.src import account
from server.src.cloud_protection import account_routes, bootstrap_time, close_response, json_bytes, open_request, parse_json
from server.src.types import ApiError, Dependencies, HandlerResult, RequestContext


def _error(error):
    payload = {'code':error.code}
    if error.retry_after_seconds is not None:
        payload['retry_after_seconds'] = error.retry_after_seconds
    return HandlerResult(error.status,{'v':1,'ok':False,'error':payload})


def dispatch_request(path: str, payload: dict, context: RequestContext, *, deps: Dependencies) -> HandlerResult:
    handlers = {
        routing.USER_ACCOUNT_REGISTER: account.register_account,
        routing.USER_OTP_SEND: account.send_registration_otp,
        routing.USER_OTP_VERIFY: account.verify_registration_otp,
        routing.USER_SESSION_LOGIN: account.login,
        routing.USER_SESSION_REFRESH: account.refresh_session,
        routing.USER_SESSION_LOGOUT: account.logout,
        routing.USER_SESSION_BOOTSTRAP: bootstrap_time,
    }
    try:
        if context.auth is not None:
            raise ApiError('INVALID_REQUEST',400)
        handler = handlers.get(path)
        if handler is None: raise ApiError('INVALID_REQUEST',400)
        return handler(payload,context,deps=deps)
    except ApiError as error:
        return _error(error)
    except Exception:
        logging.getLogger(__name__).error('INTERNAL_ERROR')
        return _error(ApiError('INTERNAL_ERROR',500))


def create_app(deps: Dependencies) -> ThreadingHTTPServer:
    class Server(ThreadingHTTPServer):
        daemon_threads = True

        def process_request(self, request, address):
            if not deps.state.http_slots.acquire(blocking=False):
                # No TLS handshake has happened yet: reject without blocking accept.
                self.shutdown_request(request)
                return
            try: super().process_request(request,address)
            except Exception:
                deps.state.http_slots.release()
                raise

        def process_request_thread(self, request, address):
            try:
                request.settimeout(cfg.HTTP_READ_SECONDS)
                request.do_handshake()
                super().process_request_thread(request,address)
            except OSError:
                self.shutdown_request(request)
            finally:
                deps.state.http_slots.release()

        def handle_error(self, request, client_address):
            logging.getLogger(__name__).error('INTERNAL_ERROR')

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(cfg.HTTP_READ_SECONDS)
            super().setup()

        def log_message(self, *args):
            pass

        def _reply(self,status,value):
            raw = json_bytes(value)
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(raw)))
            self.send_header('Connection','close')
            self.end_headers()
            self.wfile.write(raw)
            self.close_connection = True

        def _public_error(self,status,code):
            self._reply(status,{'pv':1,'error':{'code':code}})

        def send_error(self,code,message=None,explain=None):
            self._public_error(405 if code == 501 else 400,'INVALID_ENVELOPE')

        def do_POST(self):
            if self.path not in account_routes():
                self._public_error(404,'INVALID_ENVELOPE')
                return
            try:
                lengths = self.headers.get_all('Content-Length',[])
                if len(lengths) != 1 or self.headers.get('Transfer-Encoding') is not None:
                    raise ValueError()
                length = int(lengths[0])
                if not 0 < length <= cfg.HTTP_MAX_BYTES: raise ValueError()
                raw = self.rfile.read(length)
                if len(raw) != length: raise ValueError()
                envelope = parse_json(raw)
            except (ValueError,UnicodeError,OSError,RecursionError):
                self._public_error(400,'INVALID_ENVELOPE')
                return
            context = RequestContext(self.client_address[0])
            try:
                opened = open_request(self.path,envelope,context,deps=deps)
            except ApiError as error:
                self._public_error(error.status,error.code)
                return
            # Anonymous account routes must reject an injected auth object after opening.
            if opened.auth is not None:
                result = _error(ApiError('INVALID_REQUEST',400))
            else:
                result = dispatch_request(self.path,opened.body,context,deps=deps)
            try: self._reply(result.status,close_response(opened,result))
            finally: del opened

    server = Server((deps.settings.server_bind_host,deps.settings.server_bind_port),Handler)
    server.deps = deps
    try:
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.minimum_version = ssl.TLSVersion.TLSv1_2
        tls.load_cert_chain(deps.settings.tls_cert_file,deps.settings.tls_key_file)
        server.socket.settimeout(cfg.HTTP_READ_SECONDS)
        server.socket = tls.wrap_socket(server.socket,server_side=True,do_handshake_on_connect=False)
    except (OSError,ssl.SSLError):
        server.server_close()
        raise ValueError('CONFIG_INVALID') from None
    return server
