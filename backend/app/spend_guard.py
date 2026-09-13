from time import monotonic
from uuid import uuid4
from .schemas import now


class GuardError(RuntimeError):
    pass


class SpendGuard:
    def __init__(self, store, settings, task, scope='live', batch_id=None, batch_limit=None):
        self.store, self.settings, self.task = store, settings, task
        self.scope, self.batch_id, self.batch_limit = scope, batch_id, batch_limit
        self.deadline = monotonic() + task.max_latency_seconds
        self.calls = 0
        self.reserved = 0.

    @property
    def remaining_seconds(self):
        return max(0., self.deadline - monotonic())

    def reserve(self, estimate):
        if self.calls >= self.settings.max_model_calls_per_request:
            raise GuardError('Maximum model calls reached.')
        if self.remaining_seconds < .05:
            raise GuardError('Execution deadline reached.')
        if self.task.mode == 'simulation':
            self.calls += 1
            return None
        if estimate is None:
            raise GuardError('Cost unavailable: paid execution blocked until authoritative pricing is configured.')
        if estimate < 0:
            raise GuardError('Invalid spend estimate.')
        cap = min(self.task.max_budget_usd, self.settings.max_cost_per_request)
        if self.reserved + estimate > cap + 1e-12:
            raise GuardError('Request budget cannot cover this model call.')
        token = str(uuid4())
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            total = db.execute('SELECT COALESCE(SUM(COALESCE(actual,reserved)),0) FROM spend').fetchone()[0]
            if total + estimate > self.settings.max_total_dev_spend:
                raise GuardError('Total development spend limit reached.')
            scope_limit = getattr(self.settings, f'max_{self.scope}_spend', None)
            if scope_limit is not None:
                scoped = db.execute('SELECT COALESCE(SUM(COALESCE(actual,reserved)),0) FROM spend WHERE scope=?', (self.scope,)).fetchone()[0]
                if scoped + estimate > scope_limit:
                    raise GuardError(f'{self.scope.title()} spend limit reached.')
            if self.batch_id and self.batch_limit is not None:
                batch = db.execute('SELECT COALESCE(SUM(COALESCE(actual,reserved)),0) FROM spend WHERE batch_id=?', (self.batch_id,)).fetchone()[0]
                if batch + estimate > self.batch_limit:
                    raise GuardError('Experiment budget reached.')
            db.execute('INSERT INTO spend VALUES (?,?,?,?,?,?,?,?)', (token,self.scope,self.batch_id,self.task.task_id,estimate,None,'reserved',now()))
        self.calls += 1
        self.reserved += estimate
        return token

    def settle(self, token, actual):
        if token is None:
            return
        with self.store.connect() as db:
            previous = db.execute('SELECT reserved FROM spend WHERE id=?', (token,)).fetchone()[0]
            # Unknown usage keeps the reservation charged, including network timeouts.
            db.execute('UPDATE spend SET actual=?,state=? WHERE id=?', (actual, 'measured' if actual is not None else 'uncertain', token))
        if actual is not None:
            self.reserved += actual - previous
