import hashlib
import asyncio
from uuid import uuid4
from .schemas import TaskRequest, now
from . import registry, policy


def should_shadow(run_id,rate):
    return int(hashlib.sha256(run_id.encode()).hexdigest()[:8],16)/0xffffffff < rate


async def execute_shadow(controller,production):
    if controller.settings.dry_run_mode and production.task.mode=='live':
        return {'status':'unavailable','detail':'DRY_RUN_MODE cannot create simulated evidence for a live production result.'}
    store=controller.store
    key=production.run_id
    # Claim persisted before awaiting: duplicate requests cannot inflate evidence.
    if store.get('shadow',key): return store.get('shadow',key)
    alternatives=[r for r in registry.recipes(store,production.task.mode) if r.recipe_id!=production.selected_recipe.recipe_id]
    if not alternatives: return {'status':'unavailable','detail':'No alternative verified recipe'}
    counts={r.recipe_id:sum(p.get('shadow_recipe')==r.recipe_id for p in store.list('shadow')) for r in alternatives}
    # Finish an existing candidate's evidence batch before spreading samples thinly.
    collecting={p['recipe_preferences'][0] for p in store.list('policies') if p['mode']==production.task.mode and p['task_family']==production.profile.task_family and p['status']=='shadow' and p['evidence_count']<controller.settings.policy_min_evidence}
    candidate=min(alternatives,key=lambda r:(r.recipe_id not in collecting,counts[r.recipe_id],r.max_output_tokens))
    item=dict(id=key,production_run=production.run_id,production_recipe=production.selected_recipe.recipe_id,
        shadow_recipe=candidate.recipe_id,family=production.profile.task_family,mode=production.task.mode,status='running',created_at=now())
    store.put('shadow',key,item)
    store.event(key,'shadow','active','Testing an alternative recipe after production output was finalized')
    task=production.task.model_copy(update={'task_id':str(uuid4())})
    result=await controller.run(task,scope='shadow',forced_recipe=candidate.recipe_id,use_cache=False)
    item.update(status='completed' if result.status=='completed' else 'failed',shadow_run=result.run_id,
        production_quality=production.quality,shadow_quality=result.quality or 0,
        production_cost=production.total_cost,shadow_cost=result.total_cost,
        production_latency=production.total_latency,shadow_latency=result.total_latency,
        production_sla=production.sla_hit,shadow_sla=result.sla_hit,error=result.error)
    store.put('shadow',key,item)
    if item['status']=='completed':
        store.event(key,'compare','complete','Comparing paired quality, cost, latency and SLA',comparison=item)
        candidate_policy=policy.update_policy(store,controller.settings,task.mode,production.profile.task_family,candidate.recipe_id)
        item['policy_id']=candidate_policy.policy_id
        item['promotion']=candidate_policy.comparison
        store.put('shadow',key,item)
        store.event(key,'learning','complete','Shadow evidence updated the versioned policy candidate',policy_id=candidate_policy.policy_id,status_detail=candidate_policy.status)
        if production.task.mode=='live' and controller.tracing.client:
            try:
                from weave import EvaluationLogger
                client=controller.tracing.client
                comparison=client.create_call('optara.shadow_compare',{'production_run':key,'shadow_run':result.run_id},use_stack=False)
                learned=client.create_call('optara.update_policy',{'policy_id':candidate_policy.policy_id},parent=comparison,use_stack=False)
                client.finish_call(learned,output=candidate_policy.model_dump(mode='json'))
                client.finish_call(comparison,output=item)
                logger=EvaluationLogger(name=f'Optara shadow {key[:8]}',model='Paired execution recipes',dataset='Production task reference checks')
                for label,run in [('production',production),('shadow',result)]:
                    logger.log_example(inputs={'production_run':key,'role':label},output={'run_id':run.run_id,'recipe':run.selected_recipe.recipe_id,'cost':run.total_cost,'latency':run.total_latency},scores={'quality':run.quality or 0,'sla':run.sla_hit})
                logger.log_summary({'policy_id':candidate_policy.policy_id,'eligible':candidate_policy.comparison['eligible']})
                await asyncio.wait_for(asyncio.to_thread(client.flush),20)
                await asyncio.wait_for(asyncio.to_thread(client.get_call,comparison.id),15)
                item['comparison_trace_url']=comparison.ui_url
                item['evaluation_url']=logger.ui_url
            except Exception:
                item['trace_status']='Shadow comparison upload not verified'
            store.put('shadow',key,item)
    # Production output, quality, spend, latency and SLA are immutable.
    saved=store.get('runs',key)
    if saved:
        saved['shadow_result']=item
        store.put('runs',key,saved)
    store.event(key,'shadow','complete' if item['status']=='completed' else 'warning','Shadow comparison recorded; production result unchanged',comparison=item)
    return item
