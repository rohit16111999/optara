import math
from statistics import mean,stdev
from uuid import uuid4
from .schemas import Policy, now


def assess(pairs,minimum,quality_tolerance=.02,confidence_z=1.96,min_latency_improvement=.01):
    if len(pairs)<minimum: return False,'Collecting evidence',{}
    dq=[p['shadow_quality']-p['production_quality'] for p in pairs]
    dc=[p['production_cost']-p['shadow_cost'] for p in pairs if p['production_cost'] is not None and p['shadow_cost'] is not None]
    dl=[p['production_latency']-p['shadow_latency'] for p in pairs]
    ds=[int(p['shadow_sla'])-int(p['production_sla']) for p in pairs]
    lower=lambda xs: mean(xs)-confidence_z*stdev(xs)/math.sqrt(len(xs)) if len(xs)>1 else float('-inf')
    quality_safe=lower(dq)>=-quality_tolerance
    improves=(len(dc)==len(pairs) and lower(dc)>0) or lower(dl)>min_latency_improvement or lower(ds)>0
    stats={'quality_delta':mean(dq),'quality_delta_lower':lower(dq),'cost_saving':mean(dc) if dc else None,'latency_saving':mean(dl),'sla_delta':mean(ds)}
    return quality_safe and improves,('Promotion eligible' if quality_safe and improves else 'No statistically supported improvement'),stats


def update_policy(store,settings,mode,family,recipe_id):
    # Each pair must be a distinct production task; repeated shadow clicks cannot
    # manufacture evidence. Policies are versioned within family and mode.
    pairs=[p for p in store.list('shadow',10000) if p['mode']==mode and p['family']==family and p['shadow_recipe']==recipe_id and p['status']=='completed']
    unique={p['production_run']:p for p in reversed(pairs)}
    pairs=list(unique.values())
    existing=[p for p in store.list('policies') if p['mode']==mode and p['task_family']==family]
    active=next((p for p in existing if p['recipe_preferences']==[recipe_id] and p['status'] in ('candidate','shadow')),None)
    if active: policy=Policy(**active)
    else:
        policy=Policy(policy_id=str(uuid4()),version=max([p['version'] for p in existing],default=0)+1,task_family=family,
            recipe_preferences=[recipe_id],creation_reason='Alternative recipe observed in an isolated paired shadow experiment.',mode=mode)
    eligible,reason,stats=assess(pairs,settings.policy_min_evidence,settings.policy_quality_tolerance,settings.policy_confidence_z,settings.policy_min_latency_improvement)
    policy.evidence_count=len(pairs)
    policy.confidence=min(.99,len(pairs)/(len(pairs)+5))
    policy.status='shadow' if pairs else 'candidate'
    policy.comparison={**stats,'eligible':eligible,'reason':reason,'required_samples':settings.policy_min_evidence}
    if len(pairs)>=settings.policy_min_evidence and stats.get('quality_delta_lower',0)<-settings.policy_quality_tolerance:
        policy.status='rejected'
    store.put('policies',policy.policy_id,policy)
    return policy


def promote(store,settings,policy_id):
    data=store.get('policies',policy_id)
    if not data: raise ValueError('Policy not found')
    if data['status'] not in ('candidate','shadow'): raise ValueError('Only a candidate currently under evaluation may be promoted.')
    policy=update_policy(store,settings,data['mode'],data['task_family'],data['recipe_preferences'][0])
    if policy.policy_id!=policy_id or not policy.comparison.get('eligible'): raise ValueError('Promotion requires sufficient paired evidence, quality protection and a demonstrated improvement.')
    with store.connect() as db:
        import json
        db.execute('BEGIN IMMEDIATE')
        rows=db.execute("SELECT id,body FROM documents WHERE collection='policies'").fetchall()
        for row in rows:
            old=json.loads(row['body'])
            if old['mode']==policy.mode and old['task_family']==policy.task_family and old['status']=='production':
                old['status']='rejected'; old['comparison']['reason']='Superseded by a newer production version'
                db.execute('UPDATE documents SET body=?,updated=? WHERE collection=? AND id=?',(json.dumps(old),now(),'policies',row['id']))
        policy.status='production'; policy.promoted_at=now()
        db.execute('UPDATE documents SET body=?,updated=? WHERE collection=? AND id=?',(policy.model_dump_json(),now(),'policies',policy_id))
    return policy
