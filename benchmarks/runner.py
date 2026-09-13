import json
from statistics import mean,median
from uuid import uuid4
from backend.app.config import ROOT
from backend.app.schemas import TaskRequest, now
from backend.app import registry
from backend.app.history import expected
from backend.app.evaluator import VERSION


def suite(): return json.loads((ROOT/'benchmarks/tasks/suite.json').read_text())


def summarize(runs):
    completed=[r for r in runs if r.status=='completed']
    costs=[r.total_cost for r in runs if r.total_cost is not None]
    successes=sum(r.sla_hit for r in runs)
    return dict(tasks=len(runs),completed=len(completed),mean_quality=mean([r.quality or 0 for r in runs]) if runs else None,
        mean_cost=mean(costs) if costs and len(costs)==len(runs) else None,median_cost=median(costs) if costs else None,
        mean_latency=mean(r.total_latency for r in runs) if runs else None,sla_hit_rate=successes/len(runs) if runs else None,
        cost_per_success=sum(costs)/successes if successes and len(costs)==len(runs) else None)


def baseline_recipes(store,mode,available):
    specs={m.model_id:m for m in registry.models(store,mode)}
    observations=[o for o in store.list('observations',10000) if o['mode']==mode and o.get('evaluator_version','v1')==VERSION]
    measured_costs={r.recipe_id:[o['cost'] for o in observations if o['recipe_id']==r.recipe_id and o['cost'] is not None] for r in available}
    measured_cost_recipes=[r for r in available if measured_costs[r.recipe_id]]
    cheap=min(measured_cost_recipes,key=lambda r:(mean(measured_costs[r.recipe_id]),r.recipe_id)) if measured_cost_recipes else min(available,key=lambda r:((specs[r.model_id].output_price_per_million or 0)*r.max_output_tokens,r.recipe_id))
    qualities={r.recipe_id:[o['quality'] for o in observations if o['recipe_id']==r.recipe_id] for r in available}
    measured=[r for r in available if qualities[r.recipe_id]]
    strong=max(measured,key=lambda r:mean(qualities[r.recipe_id])) if measured else None
    return cheap,strong


async def run_experiment(controller,job,kind,mode,max_models=2,max_cost=.03,task_count=3):
    if controller.settings.dry_run_mode: mode='simulation'
    store=controller.store
    available=registry.recipes(store,mode)
    model_ids=list(dict.fromkeys(r.model_id for r in available))[:max_models]
    available=[r for r in available if r.model_id in model_ids]
    if not available: raise ValueError('No verified recipes available. Discover W&B models first.')
    tasks=suite()[:task_count]
    report=dict(id=job,kind=kind,mode=mode,status='running',created_at=now(),groups={},runs=[],max_cost=max_cost,evaluator_version=VERSION,notes=[],recipe_pool=[r.recipe_id for r in available])
    store.put('experiments',job,report)
    if kind=='calibration':
        strategies={r.recipe_id:r.recipe_id for r in available}
    else:
        cheap,strong=baseline_recipes(store,mode,available)
        if strong is None:
            raise ValueError('Always Strong needs measured quality evidence. Run a small calibration first; no model is assumed strongest.')
        strategies={'Always Cheap':cheap.recipe_id,'Always Strong':strong.recipe_id,'Optara':None}
        report['baseline_recipes']={'Always Cheap':cheap.recipe_id,'Always Strong':strong.recipe_id}
        report['notes'].append('Baselines fixed before evaluation; identical tasks, constraints, evaluators and no cache. Small, in-sample demonstration; not a generalization claim.')
    logger=None
    if mode=='live' and controller.tracing.client:
        try:
            from weave import EvaluationLogger
            logger=EvaluationLogger(name=f'Optara {kind} {job[:8]}',model='Optara execution recipes',dataset='optara-suite-v1')
        except Exception: report['notes'].append('Weave evaluation logger unavailable')
    for label,fixed in strategies.items():
        outcomes=[]
        for item in tasks:
            task=TaskRequest(prompt=item['prompt'],task_family=item['task_family'],evaluation_spec=item.get('evaluation_spec',{}),mode=mode,
                quality_target=.9,max_budget_usd=min(.02,max_cost),max_latency_seconds=45)
            result=await controller.run(task,scope=kind,forced_recipe=fixed,use_cache=False,batch_id=job,batch_limit=max_cost,allowed_recipes=[r.recipe_id for r in available])
            outcomes.append(result); report['runs'].append({'run_id':result.run_id,'strategy':label,'task_id':item['id']})
            if logger:
                try: logger.log_example(inputs={'task_id':item['id'],'strategy':label},output={'answer':result.output,'tokens':sum(e.total_tokens for e in result.executions),'cost':result.total_cost},scores={'quality':result.quality or 0,'sla':result.sla_hit})
                except Exception: report['notes'].append('An evaluation row could not be logged')
            report['groups'][label]=summarize(outcomes)
            store.put('experiments',job,report)
        report['groups'][label]=summarize(outcomes)
    if logger:
        try:
            logger.log_summary({'strategies':len(strategies),'max_cost':max_cost})
            report['evaluation_url']=logger.ui_url
        except Exception: report['notes'].append('Weave evaluation summary unavailable')
    report['status']='completed'; report['finished_at']=now()
    report['total_cost']=sum(r['mean_cost']*r['tasks'] for r in report['groups'].values()) if all(r['mean_cost'] is not None for r in report['groups'].values()) else None
    store.put('experiments',job,report)
    return report
