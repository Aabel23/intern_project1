"""RAM relay: app question -> machine long-poll -> machine result -> app (contracts relay-status + v2 D7/D8).

One process holds all state. Deadlines use time.monotonic so Condition waits and expiry agree.
"""
from dataclasses import dataclass, field
import json
import threading
import time
from uuid import UUID
from server.configuration import skeleton as cfg
from server.src.types import ApiError, HandlerResult

INSTRUCTIONS = {'machine.status.read', 'nhan_menu', 'cap_nhat_menu', 'nhan_kho', 'nap_kho', 'nhan_ve_qr'}
RESULT_ERROR_CODES = {'COMMAND_FAILED','UNSUPPORTED_INSTRUCTION','INVALID_DATA','MACHINE_READ_FAILED','COMMAND_EXPIRED'}


@dataclass
class Pending:
    request_id: str
    user_id: str
    instruction: str
    data: dict
    fingerprint: str
    deadline: float
    delivered: bool = False
    terminal: HandlerResult | None = None


@dataclass
class Terminal:
    user_id: str
    fingerprint: str
    result: HandlerResult
    expires: float


@dataclass
class RelayHub:
    relay_seconds: float = cfg.RELAY_SECONDS
    poll_seconds: float = cfg.POLL_SECONDS
    online_grace: float = cfg.ONLINE_GRACE_SECONDS
    terminal_seconds: float = cfg.TERMINAL_RELAY_SECONDS
    clock: object = time.monotonic
    wall_ms: object = lambda: int(time.time()*1000)
    cond: threading.Condition = field(default_factory=threading.Condition)
    pending: dict = field(default_factory=dict)     # machine_id -> Pending
    terminals: dict = field(default_factory=dict)   # (machine_id, request_id) -> Terminal
    poll_generation: dict = field(default_factory=dict)
    open_polls: dict = field(default_factory=dict)  # machine_id -> generation currently waiting
    last_poll: dict = field(default_factory=dict)   # machine_id -> (monotonic, wall ms)

    # ------------------------------------------------------------ presence

    def is_online(self, machine_id):
        with self.cond:
            return self._online(machine_id)

    def _online(self, machine_id):
        if machine_id in self.open_polls: return True
        seen = self.last_poll.get(machine_id)
        return seen is not None and self.clock()-seen[0] <= self.online_grace

    def last_seen_ms(self, machine_id):
        with self.cond:
            if machine_id in self.open_polls: return self.wall_ms()
            seen = self.last_poll.get(machine_id)
            return None if seen is None else seen[1]

    def _prune(self, now):
        for key in [k for k,v in self.terminals.items() if v.expires <= now]: del self.terminals[key]
        for machine_id in [m for m,p in self.pending.items() if p.terminal is None and p.deadline <= now]:
            self._finish(machine_id, HandlerResult(504,{'v':1,'ok':False,'error':{'code':'MACHINE_TIMEOUT'}}))

    def _finish(self, machine_id, result):
        item = self.pending.pop(machine_id)
        item.terminal = result
        self.terminals[(machine_id,item.request_id)] = Terminal(item.user_id,item.fingerprint,result,self.clock()+self.terminal_seconds)
        self.cond.notify_all()

    # ------------------------------------------------------------ app side

    def send(self, *, user_id, machine_id, request_id, instruction, data, retry, owner_lookup):
        fingerprint = json.dumps([instruction,data],sort_keys=True,separators=(',',':'))
        if owner_lookup(machine_id) != user_id: raise ApiError('FORBIDDEN',403)
        with self.cond:
            now = self.clock()
            self._prune(now)
            done = self.terminals.get((machine_id,request_id))
            if done is not None:
                if done.user_id != user_id or done.fingerprint != fingerprint: raise ApiError('REQUEST_CONFLICT',409)
                return done.result
            item = self.pending.get(machine_id)
            if item is not None and item.request_id == request_id:
                if item.user_id != user_id or item.fingerprint != fingerprint: raise ApiError('REQUEST_CONFLICT',409)
            elif retry:
                # Restart or eviction lost the record; never turn a retry into a fresh write.
                raise ApiError('REQUEST_GONE',410)
            elif item is not None:
                raise ApiError('BUSY',409)
            elif not self._online(machine_id):
                raise ApiError('MACHINE_OFFLINE',503)
            else:
                item = Pending(request_id,user_id,instruction,data,fingerprint,now+self.relay_seconds)
                self.pending[machine_id] = item
                self.cond.notify_all()
            while item.terminal is None:
                remaining = item.deadline-self.clock()
                if remaining <= 0:
                    self._prune(self.clock())
                    break
                self.cond.wait(remaining)
            result = item.terminal
        # Permission is re-read before a machine answer reaches the app.
        if result.status == 200 and owner_lookup(machine_id) != user_id: raise ApiError('FORBIDDEN',403)
        return result

    # ------------------------------------------------------------ machine side

    def poll(self, machine_id):
        with self.cond:
            generation = self.poll_generation.get(machine_id,0)+1
            self.poll_generation[machine_id] = generation
            self.open_polls[machine_id] = generation
            # Newest poll wins: an older poll the NAT dropped silently returns now.
            self.cond.notify_all()
            deadline = self.clock()+self.poll_seconds
            try:
                while True:
                    now = self.clock()
                    self._prune(now)
                    if self.poll_generation[machine_id] != generation: return None
                    item = self.pending.get(machine_id)
                    if item is not None and not item.delivered:
                        item.delivered = True
                        return {'v':1,'request_id':item.request_id,'machine_id':machine_id,'instruction':item.instruction,
                                'data':item.data,'remaining_ms':max(0,int((item.deadline-now)*1000))}
                    if now >= deadline: return None
                    self.cond.wait(min(deadline-now,1.0))
            finally:
                if self.open_polls.get(machine_id) == generation: del self.open_polls[machine_id]
                self.last_poll[machine_id] = (self.clock(),self.wall_ms())

    def result(self, machine_id, request_id, result):
        with self.cond:
            self._prune(self.clock())
            self.last_poll[machine_id] = (self.clock(),self.wall_ms())
            item = self.pending.get(machine_id)
            if item is None or item.request_id != request_id:
                if (machine_id,request_id) in self.terminals: raise ApiError('RESULT_ALREADY_FINAL',409)
                raise ApiError('RESULT_EXPIRED',410)
            payload = {'request_id':request_id,'machine_id':machine_id,'source':'machine',
                       'received_at':self.wall_ms(),'result':result}
            self._finish(machine_id,HandlerResult(200,{'v':1,'ok':True,'data':payload}))


# ---------------------------------------------------------------- route handlers

def _schema(body, required, optional=()):
    if not isinstance(body,dict) or type(body.get('v')) is not int: raise ApiError('INVALID_REQUEST',400)
    if body['v'] != 1: raise ApiError('UNSUPPORTED_VERSION',400)
    keys = set(body)-{'v'}
    if not set(required) <= keys or not keys <= set(required)|set(optional): raise ApiError('INVALID_REQUEST',400)


def _uuid4(value):
    try: parsed = UUID(value)
    except (ValueError,TypeError,AttributeError): raise ApiError('INVALID_REQUEST',400) from None
    if parsed.version != 4 or str(parsed) != value: raise ApiError('INVALID_REQUEST',400)
    return value


def _slot(semaphore):
    if not semaphore.acquire(blocking=False): raise ApiError('SERVICE_UNAVAILABLE',503)
    return semaphore


def command_send(body, context, *, deps):
    from server.src.devices import owner_of
    _schema(body,{'request_id','machine_id','instruction','data'},{'retry'})
    if body['instruction'] not in INSTRUCTIONS or not isinstance(body['data'],dict): raise ApiError('INVALID_REQUEST',400)
    if body.get('retry',False) not in (True,False): raise ApiError('INVALID_REQUEST',400)
    if len(json.dumps(body['data'],ensure_ascii=False).encode('utf-8')) > cfg.RELAY_DATA_MAX_BYTES: raise ApiError('INVALID_REQUEST',400)
    slot = _slot(deps.state.relay_slots)
    try:
        return deps.state.relay.send(user_id=context.auth.user_id,machine_id=_uuid4(body['machine_id']),
                                     request_id=_uuid4(body['request_id']),instruction=body['instruction'],
                                     data=body['data'],retry=body.get('retry',False),
                                     owner_lookup=lambda machine_id: owner_of(deps,machine_id))
    finally:
        slot.release()


def command_poll(body, context, *, deps):
    _schema(body,set())
    slot = _slot(deps.state.poll_slots)
    try:
        command = deps.state.relay.poll(context.machine['id'])
    finally:
        slot.release()
    return HandlerResult(200,{'v':1,'ok':True,'data':{'command':command}})


def _valid_result(result):
    if not isinstance(result,dict) or type(result.get('ok')) is not bool: return False
    if result['ok']: return set(result) == {'ok','data'} and isinstance(result['data'],dict)
    error = result.get('error')
    return (set(result) == {'ok','error'} and isinstance(error,dict) and error.get('code') in RESULT_ERROR_CODES
            and set(error) <= {'code','message'} and isinstance(error.get('message',''),str))


def result_send(body, context, *, deps):
    _schema(body,{'request_id','result'})
    if not _valid_result(body['result']): raise ApiError('INVALID_REQUEST',400)
    deps.state.relay.result(context.machine['id'],_uuid4(body['request_id']),body['result'])
    return HandlerResult(200,{'v':1,'ok':True,'data':{'accepted':True}})
