"""L-01S over LAN HTTP (SERVER_TRANSPORT=http, loopback bind + MySQL fixture TEST_DB_*):
wrong machine signature, wrong role and missing session are all refused, same as over HTTPS."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'version1.1'))

from argon2 import PasswordHasher
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, x25519

from machine.config import identity as machine_identity
from machine.server_connection.cloud_protection import CloudError
from machine.server_connection.machine_server_request import ServerClient
from server.configuration import routing
from server.src import devices
from server.src.crypto_keys import ServerKeys, b64u, decode_b64u
from server.src.cloud_protection import verify_machine_signature
from server.src.database import open_connection, transaction
from server.src.http import create_app
from server.src.relay import RelayHub
from server.src.types import Dependencies, create_runtime_state
from test_machine_relay import AppClient, TABLES
from test_smtp import settings


@unittest.skipUnless(os.environ.get('TEST_DB_NAME'), 'TEST_DB_* isolated MySQL fixture required')
class LanHttpAuthTests(unittest.TestCase):
    def setUp(self):
        name = os.environ['TEST_DB_NAME']
        if not name.endswith('_test'): self.skipTest('fixture DB name must end _test')
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        config = replace(settings(db_host=os.environ['TEST_DB_HOST'], db_port=int(os.environ['TEST_DB_PORT']), db_name=name,
                                  db_user=os.environ['TEST_DB_USER'], db_password=os.environ['TEST_DB_PASSWORD'],
                                  server_bind_port=0, tls_cert_file='', tls_key_file=''), server_transport='http')
        self.keys = ServerKeys(x25519.X25519PrivateKey.generate(), ec.generate_private_key(ec.SECP256R1()), {})
        boot_ms = int(time.time() * 1000) - 1000
        state = create_runtime_state(config, boot_ms)
        state.relay = RelayHub(relay_seconds=2, poll_seconds=1, online_grace=1.5, terminal_seconds=5)
        self.deps = Dependencies(config, lambda: open_connection(config), lambda: datetime.now(timezone.utc), time.monotonic, None, self.keys, state)
        with transaction(self.deps.connect) as connection, closing(connection.cursor()) as cursor:
            for table in TABLES: cursor.execute('DELETE FROM ' + table)
        self.server = create_app(self.deps)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        self.trust = {'v': 1,
                      'hpke': {'kid': 'server-hpke-1', 'public_key': b64u(self.keys.hpke_private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))},
                      'signing': {'kid': 'server-sign-1', 'public_key': b64u(self.keys.signing_private.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))}}
        self.identity = machine_identity.provision(self.dir / 'machine', '00000000abcdef01')
        self.registered = devices.register_device(self.deps.connect, self.identity.serial, 'FlexMix-Test', self.identity.public_key,
                                                  now=datetime.now(timezone.utc).replace(tzinfo=None))
        self.machine = ServerClient(self.base, self.identity, self.trust)

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.tmp.cleanup()

    def app(self):
        return AppClient(self.base, self.keys, None, lambda: int(time.time() * 1000))

    def user(self, email):
        with transaction(self.deps.connect) as connection, closing(connection.cursor()) as cursor:
            cursor.execute('INSERT INTO users(id,email,password_hash,verified_at) VALUES(%s,%s,%s,%s)',
                           (str(uuid4()), email, PasswordHasher().hash('TEST_ONLY_PASSWORD_LONG'), datetime(2026, 1, 1)))
        client = self.app()
        status, body = client.post(routing.USER_SESSION_LOGIN, {'v': 1, 'email': email, 'password': 'TEST_ONLY_PASSWORD_LONG'})
        self.assertEqual(status, 200, body)
        client.token = body['data']['access_token']
        return client

    def claim(self, app):
        status, begin = app.post(routing.USER_MACHINE_ACTIVATE, {'v': 1, 'step': 'begin', 'serial': self.identity.serial})
        self.assertEqual(status, 200, begin)
        data = begin['data']
        verify_machine_signature(decode_b64u(self.trust['signing']['public_key']), devices.challenge_bytes(data['challenge']),
                                 decode_b64u(data['server_challenge_signature']))
        binding = str(uuid4())
        proof = self.identity.sign(devices.accept_bytes(data['challenge'], binding))
        status, body = app.post(routing.USER_MACHINE_ACTIVATE, {'v': 1, 'step': 'complete', 'claim_id': data['claim_id'],
                                                                 'machine_proof': b64u(proof), 'local_session_binding': binding})
        self.assertEqual(status, 200, body)

    def relay_request(self, **changes):
        return {'v': 1, 'request_id': str(uuid4()), 'machine_id': self.registered['machine_id'],
                'instruction': 'machine.status.read', 'data': {}, **changes}

    def test_http_machine_happy_path_baseline(self):
        # Sanity: the honest machine works over HTTP, so the refusals below are due to the signature, not the transport.
        self.assertEqual(self.machine.hello()['machine_id'], self.registered['machine_id'])
        self.assertIsNone(self.machine.poll_command())

    def test_machine_with_wrong_signature_refused_on_poll_and_result(self):
        self.machine.hello()
        # Attacker knows the victim key_id but signs with its own key.
        attacker = machine_identity.provision(self.dir / 'attacker', '00000000abcdef09')
        forged = replace(attacker, serial=self.identity.serial, key_id=self.identity.key_id)
        client = ServerClient(self.base, forged, self.trust)
        client._server_time, client._receipt = int(time.time() * 1000), client.monotonic()
        with self.assertRaises(CloudError) as raised: client.poll_command()
        self.assertEqual((raised.exception.code, raised.exception.status), ('INVALID_ENVELOPE', 400))
        with self.assertRaises(CloudError) as raised: client.send_result(str(uuid4()), {'ok': True, 'data': {}})
        self.assertEqual((raised.exception.code, raised.exception.status), ('INVALID_ENVELOPE', 400))
        with self.assertRaises(CloudError) as raised: client.hello()
        self.assertEqual(raised.exception.code, 'INVALID_ENVELOPE')
        # An unregistered key is refused as well.
        with self.assertRaises(CloudError) as raised: ServerClient(self.base, attacker, self.trust).hello()
        self.assertEqual(raised.exception.code, 'UNKNOWN_KEY')

    def test_forged_result_does_not_complete_pending_relay(self):
        owner = self.user('owner@example.invalid')
        self.claim(owner)
        self.assertIsNone(self.machine.poll_command())
        request = self.relay_request()
        attacker = machine_identity.provision(self.dir / 'attacker', '00000000abcdef09')
        forged = replace(attacker, serial=self.identity.serial, key_id=self.identity.key_id)
        client = ServerClient(self.base, forged, self.trust)
        client._server_time, client._receipt = int(time.time() * 1000), client.monotonic()
        with ThreadPoolExecutor(1) as pool:
            sent = pool.submit(owner.post, routing.MACHINE_COMMAND_SEND, request)
            time.sleep(.3)
            with self.assertRaises(CloudError) as raised:
                client.send_result(request['request_id'], {'ok': True, 'data': {'fake': True}})
            self.assertEqual(raised.exception.code, 'INVALID_ENVELOPE')
            status, body = sent.result()
        # Nobody honest answered, so the relay times out; the forged result was never accepted.
        self.assertEqual((status, body['error']['code']), (504, 'MACHINE_TIMEOUT'))

    def test_non_owner_cannot_relay_to_other_machine(self):
        owner = self.user('owner@example.invalid')
        stranger = self.user('stranger@example.invalid')
        self.claim(owner)
        self.assertIsNone(self.machine.poll_command())
        status, body = stranger.post(routing.MACHINE_COMMAND_SEND, self.relay_request())
        self.assertEqual((status, body['error']['code']), (403, 'FORBIDDEN'))
        # Stranger cannot release it either, and the owner still holds it.
        self.assertEqual(stranger.post(routing.USER_MACHINE_REMOVE, {'v': 1, 'machine_id': self.registered['machine_id']})[0], 403)
        self.assertEqual(len(owner.post(routing.USER_MACHINE_LIST, {'v': 1})[1]['data']['machines']), 1)
        self.assertEqual(stranger.post(routing.USER_MACHINE_LIST, {'v': 1})[1]['data']['machines'], [])
        # A machine id that does not exist is refused the same way.
        status, body = stranger.post(routing.MACHINE_COMMAND_SEND, self.relay_request(machine_id=str(uuid4())))
        self.assertEqual(status, 403, body)

    def test_requests_without_session_refused_on_auth_routes(self):
        anonymous = self.app()
        owner = self.user('owner@example.invalid')
        self.claim(owner)
        for route, body in ((routing.USER_MACHINE_LIST, {'v': 1}),
                            (routing.MACHINE_COMMAND_SEND, self.relay_request()),
                            (routing.USER_MACHINE_REMOVE, {'v': 1, 'machine_id': self.registered['machine_id']}),
                            (routing.USER_MACHINE_ACTIVATE, {'v': 1, 'step': 'begin', 'serial': self.identity.serial})):
            status, reply = anonymous.post(route, body)
            self.assertEqual((status, reply['error']['code']), (401, 'SESSION_EXPIRED'), (route, reply))
        # A made-up token is no better than none.
        anonymous.token = 'not-a-real-token'
        status, reply = anonymous.post(routing.USER_MACHINE_LIST, {'v': 1})
        self.assertEqual(status, 401, reply)
        # And the owner's machine was untouched.
        self.assertEqual(len(owner.post(routing.USER_MACHINE_LIST, {'v': 1})[1]['data']['machines']), 1)


if __name__ == '__main__': unittest.main()
