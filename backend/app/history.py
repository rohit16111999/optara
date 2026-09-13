import math
from uuid import uuid4
from .schemas import ExpectedMetrics, now
from .evaluator import VERSION


def observe(store, mode, family, recipe_id, quality, cost, latency, run_id, scope):
    store.put('observations', str(uuid4()), dict(mode=mode, family=family, recipe_id=recipe_id, quality=quality,
        cost=cost, latency=latency, run_id=run_id, scope=scope, evaluator_version=VERSION, created_at=now()))


def expected(store, mode, family, recipe, estimated_cost):
    rows = [r for r in store.list('observations',10000) if r['mode']==mode and r['family']==family and r['recipe_id']==recipe.recipe_id and r.get('evaluator_version','v1')==VERSION]
    n = len(rows)
    if not n:
        return ExpectedMetrics(expected_cost=estimated_cost)
    # Beta(1,1) prior: two pseudo-observations, fractional quality scores allowed.
    q = (1 + sum(r['quality'] for r in rows))/(n + 2)
    uncertainty = min(.5, 1.96 * math.sqrt(q*(1-q)/(n+3)))
    costs = [r['cost'] for r in rows if r['cost'] is not None]
    return ExpectedMetrics(expected_quality=q, expected_cost=sum(costs)/len(costs) if costs else estimated_cost,
        expected_latency=sum(r['latency'] for r in rows)/n, observations=n, uncertainty=uncertainty,
        last_updated=rows[0]['created_at'], source='Observed recipe outcomes with Beta(1,1) smoothing')
