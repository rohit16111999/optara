"""One tiny real inference through the same bounded Optara controller."""
import argparse
import asyncio
import json
from backend.app.config import Settings,credential
from backend.app.persistence import Store
from backend.app.controller import Controller
from backend.app.inference import InferenceEngine
from backend.app.schemas import TaskRequest
from backend.app.registry import register_models,recipes
from backend.integrations.wandb_inference import WandbInference
from backend.integrations.weave_integration import WeaveIntegration
from backend.integrations.wandb_history import verify_project,verify_mcp


async def verify():
    settings=Settings();store=Store(settings.optara_db_path)
    if not credential(settings):
        result={'verified':False,'blocker':'No W&B credential in environment or standard saved login. Complete scripts/login.py.','inference':False,'weave':False,'mcp':False}
        store.put('verification','latest',result)
        return result
    provider=WandbInference(settings)
    try: register_models(store,await provider.discover())
    except Exception:
        return {'verified':False,'blocker':'Authenticated W&B model discovery failed; check inference access.','inference':False,'weave':False}
    tracing=WeaveIntegration(settings);await tracing.initialize()
    available=recipes(store)
    if not available:return {'verified':False,'blocker':'No discovered models have verified pricing.'}
    # Single 32-output-token recipe, repair disabled; reference check needs no judge.
    selected=min(available,key=lambda r:r.max_output_tokens).model_copy(update={'recipe_id':'auth-verification-v1','name':'Authentication verification','max_output_tokens':32,'repair_limit':0,'verifier_enabled':False,'agents':1,'metadata':{'verification_only':True}})
    store.put('recipes',selected.recipe_id,selected)
    controller=Controller(store,settings,InferenceEngine(provider),tracing)
    task=TaskRequest(prompt='Reply with exactly: OPTARA_WANDB_OK',max_budget_usd=.002,max_latency_seconds=45)
    run=await controller.run(task,forced_recipe=selected.recipe_id,use_cache=False)
    project,mcp=await asyncio.gather(verify_project(settings),verify_mcp(settings))
    store.put('integration','project',project);store.put('integration','mcp',mcp)
    result={'verified':run.output=='OPTARA_WANDB_OK' and bool(run.trace_url),'run_id':run.run_id,'output':run.output,'inference':bool(run.executions and not run.executions[0].error),'weave':bool(run.trace_url),'mcp':mcp['available'],'tokens':sum(e.total_tokens for e in run.executions),'cost_usd':run.total_cost,'latency_seconds':run.total_latency,'trace_url':run.trace_url,'project_url':f'https://wandb.ai/{settings.project_id}','error':run.error}
    store.put('verification','latest',result)
    return result


if __name__=='__main__':
    report=asyncio.run(verify());print(json.dumps(report,indent=2));raise SystemExit(0 if report.get('verified') else 2)
