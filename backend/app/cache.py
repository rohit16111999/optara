import hashlib
import json
from datetime import datetime,timezone,timedelta
from .schemas import now

EVALUATOR_VERSION='v1'


def cache_key(task,recipe):
    # Preserve case and internal whitespace: both can change code/string semantics.
    payload=dict(prompt=task.prompt.strip(),quality=task.quality_target,spec=task.evaluation_spec,
        recipe=recipe.model_dump(),evaluator=EVALUATOR_VERSION,mode=task.mode)
    return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()


def lookup(store,task,profile,recipe):
    if not profile.cacheable: return None
    item=store.get('cache',cache_key(task,recipe))
    if item and datetime.fromisoformat(item['expires']) > datetime.now(timezone.utc): return item
    return None


def save(store,task,profile,recipe,output,evaluation):
    if profile.cacheable and evaluation.passed and evaluation.confidence >= .7:
        store.put('cache',cache_key(task,recipe),dict(output=output,evaluation=evaluation.model_dump(),created_at=now(),
            expires=(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat()))
