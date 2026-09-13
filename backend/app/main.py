import asyncio
import importlib.util
import json
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel,Field
from .config import Settings,credential
from .persistence import Store
from .schemas import TaskRequest,RunResult,now
from .controller import Controller
from .inference import InferenceEngine
from . import registry,policy
from .profiler import profile_task
from .history import expected
from .pricing import upper_cost
from .shadow import execute_shadow,should_shadow
from backend.integrations.wandb_inference import WandbInference
from backend.integrations.weave_integration import WeaveIntegration,redact
from backend.integrations.wandb_history import verify_project,verify_mcp,sync_history
from backend.integrations import aria,typesafe,wandb_sandbox
from benchmarks.runner import run_experiment


class ExperimentRequest(BaseModel):
    mode: str = Field(default='live',pattern='^(live|simulation)$')
    max_models: int = Field(default=2,ge=1,le=3)
    max_cost: float = Field(default=.03,gt=0,le=.25)
    task_count: int = Field(default=3,ge=1,le=6)


def create_app(settings=None):
    settings=settings or Settings()
    store=Store(settings.optara_db_path)
    provider=WandbInference(settings)
    tracing=WeaveIntegration(settings)
    controller=Controller(store,settings,InferenceEngine(provider),tracing)
    workers=set()
    submitting=0

    def spawn(coro):
        worker=asyncio.create_task(coro)
        workers.add(worker)
        worker.add_done_callback(workers.discard)
        return worker

    @asynccontextmanager
    async def lifespan(app):
        for run in store.list('runs',10000):
            if run['status'] in ('queued','running'):
                run['status']='interrupted'; run['error']='Backend restarted; uncertain spend reservations retained.'
                store.put('runs',run['run_id'],run)
                store.event(run['run_id'],'done','failed',run['error'],result=run)
        for collection in ('experiments','shadow'):
            for job in store.list(collection):
                if job['status']=='running':
                    job['status']='interrupted'; job['error']='Backend restarted; rerun explicitly.'
                    store.put(collection,job['id'],job)
        yield
        for worker in list(workers): worker.cancel()
        await asyncio.gather(*workers,return_exceptions=True)

    app=FastAPI(title='Optara',version='0.1.0',lifespan=lifespan)
    app.state.controller=controller
    app.state.store=store
    allowed_origins=[origin.strip().rstrip('/') for origin in settings.allowed_origins.split(',') if origin.strip()]
    app.add_middleware(CORSMiddleware,allow_origins=allowed_origins,allow_methods=['GET','POST'],allow_headers=['Content-Type','Last-Event-ID'])

    @app.middleware('http')
    async def local_requests(request:Request,call_next):
        if request.method=='POST':
            origin=request.headers.get('origin')
            if origin and origin not in allowed_origins:
                return JSONResponse({'detail':'Origin is not authorized for local control-plane changes.'},403)
            try: length=int(request.headers.get('content-length','0'))
            except ValueError: return JSONResponse({'detail':'Invalid request length'},400)
            if length>100000: return JSONResponse({'detail':'Request too large'},413)
        return await call_next(request)

    @app.get('/api/health')
    def health(): return {'status':'ok','product':'Optara','version':'0.1.0','active_workers':len(workers)}

    @app.get('/api/status/integrations')
    def integrations():
        inference=store.get('integration','inference') or {'available':False,'detail':'Not yet verified' if credential(settings) else 'W&B login required'}
        return {'inference':inference,'weave':{'available':tracing.status=='connected','detail':tracing.status},
            'mcp':store.get('integration','mcp') or {'available':False,'detail':'Configured endpoint; authentication not verified'},
            'project':store.get('integration','project') or {'available':False,'detail':'Project access not verified'},
            'aria':aria.status(),'typesafe':typesafe.status(),'sandbox':wandb_sandbox.status(),
            'marimo':{'available':bool(importlib.util.find_spec('marimo')),'detail':'Local experiment app installed · start separately'},
            'project_url':f'https://wandb.ai/{settings.project_id}','weave_url':f'https://wandb.ai/{settings.project_id}/weave',
            'spend':{'total':store.spend_total(),'limit':settings.max_total_dev_spend,'shadow':store.spend_total('shadow')},
            'default_mode':'simulation' if settings.dry_run_mode else 'live','limits':{'max_request_cost':settings.max_cost_per_request,'calls':settings.max_model_calls_per_request,'repairs':settings.max_repairs_per_request,'shadow_rate':settings.shadow_exploration_rate,'policy_min_evidence':settings.policy_min_evidence}}

    @app.post('/api/status/verify')
    async def verify():
        # Read-only discovery/auth checks. No inference and no calibration.
        project,mcp=await asyncio.gather(verify_project(settings),verify_mcp(settings))
        store.put('integration','project',project); store.put('integration','mcp',mcp)
        try:
            found=await provider.discover()
            registry.register_models(store,found)
            store.put('integration','discovery',{'available':True,'count':len(found),'checked_at':now()})
        except Exception as e:
            store.put('integration','discovery',{'available':False,'detail':str(e) if isinstance(e,RuntimeError) else 'Discovery unavailable','checked_at':now()})
        if credential(settings): await tracing.initialize()
        return {**integrations(),'discovery':store.get('integration','discovery')}

    @app.post('/api/history/sync')
    async def sync(): return await sync_history(tracing,store)

    @app.get('/api/models')
    def models(mode:str=Query('live',pattern='^(live|simulation)$')): return registry.models(store,mode)

    @app.get('/api/recipes')
    def recipes(mode:str=Query('live',pattern='^(live|simulation)$'),family:str='coding'):
        specs={m.model_id:m for m in registry.models(store,mode)}
        return [{'recipe':r.model_dump(),'metrics':expected(store,mode,family,r,upper_cost(specs[r.model_id],[{'content':''}],r.max_output_tokens)).model_dump()} for r in registry.recipes(store,mode)]

    @app.get('/api/runs')
    def runs(mode:str='live',limit:int=Query(30,ge=1,le=100)):
        return [r for r in store.list('runs',10000) if r['task']['mode']==mode][:limit]

    @app.post('/api/runs',status_code=202)
    async def submit(task:TaskRequest):
        nonlocal submitting
        if len(workers)+submitting>=2: raise HTTPException(429,'Two jobs are already running. Wait for one to finish.')
        if task.max_budget_usd>settings.max_cost_per_request: raise HTTPException(422,f'Request budget exceeds the configured ${settings.max_cost_per_request:.2f} hard limit.')
        task=task.model_copy(update={'task_id':str(uuid4()),'prompt':redact(task.prompt,credential(settings)),'mode':'simulation' if settings.dry_run_mode else task.mode})
        submitting+=1
        try:
            if task.mode=='live' and credential(settings) and not registry.models(store):
                try: registry.register_models(store,await provider.discover())
                except Exception: pass
            if task.mode=='live' and credential(settings) and not tracing.client: await tracing.initialize()
        finally:
            submitting-=1
        store.put('runs',task.task_id,RunResult(run_id=task.task_id,task=task))
        async def work():
            result=await controller.run(task)
            if result.status=='completed' and not result.cache_hit and should_shadow(result.run_id,settings.shadow_exploration_rate):
                await execute_shadow(controller,result)
        spawn(work())
        return {'run_id':task.task_id,'events_url':f'/api/runs/{task.task_id}/events'}

    @app.get('/api/runs/{run_id}')
    def get_run(run_id:str):
        run=store.get('runs',run_id)
        if not run: raise HTTPException(404,'Run not found')
        return run

    @app.get('/api/runs/{run_id}/event-history')
    def event_history(run_id:str):
        if not store.get('runs',run_id): raise HTTPException(404,'Run not found')
        return store.events(run_id)

    @app.get('/api/runs/{run_id}/events')
    async def events(run_id:str,request:Request,after:int=0):
        if not store.get('runs',run_id): raise HTTPException(404,'Run not found')
        try: cursor=max(after,int(request.headers.get('last-event-id','0')))
        except ValueError: cursor=after
        async def stream():
            nonlocal cursor
            heartbeat=0
            while not await request.is_disconnected():
                batch=store.events(run_id,cursor)
                for event in batch:
                    cursor=event['sequence']
                    yield f'id: {cursor}\ndata: {json.dumps(event)}\n\n'
                run=store.get('runs',run_id)
                if run['status'] in ('completed','failed','interrupted') and any(e['stage']=='done' for e in batch): break
                # A reconnect after the final event still returns a final state.
                if not batch and run['status'] in ('completed','failed','interrupted'):
                    final=store.events(run_id)
                    if any(e['stage']=='done' for e in final): break
                heartbeat+=1
                if heartbeat%40==0: yield ': heartbeat\n\n'
                await asyncio.sleep(.15)
        return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

    @app.get('/api/policies')
    def policies(mode:str='live'): return [p for p in store.list('policies') if p['mode']==mode]

    @app.post('/api/policies/{policy_id}/promote')
    def promote_policy(policy_id:str):
        try: return policy.promote(store,settings,policy_id)
        except ValueError as e: raise HTTPException(409,str(e)) from None

    @app.get('/api/shadow')
    def shadow(mode:str='live'): return [s for s in store.list('shadow') if s['mode']==mode]

    @app.post('/api/runs/{run_id}/shadow',status_code=202)
    async def start_shadow(run_id:str):
        run=store.get('runs',run_id)
        if not run or run['status']!='completed': raise HTTPException(409,'A completed production result is required.')
        if settings.dry_run_mode and run['task']['mode']=='live': raise HTTPException(409,'DRY_RUN_MODE cannot shadow a live result. Run a Simulation task instead.')
        if run.get('cache_hit'): raise HTTPException(409,'Shadow comparisons require an uncached production execution.')
        if store.get('shadow',run_id): raise HTTPException(409,'This production run already has a shadow experiment.')
        if len(workers)>=2: raise HTTPException(429,'Worker capacity reached')
        spawn(execute_shadow(controller,RunResult(**run)))
        return {'status':'queued','production_run':run_id}

    @app.get('/api/experiments')
    def experiments(mode:str='live'): return [e for e in store.list('experiments') if e['mode']==mode]

    @app.get('/api/observations')
    def observations(mode:str='live'):
        from .evaluator import VERSION
        return [o for o in store.list('observations',10000) if o['mode']==mode and o.get('evaluator_version','v1')==VERSION]

    async def start_experiment(kind,body):
        if settings.dry_run_mode: body=body.model_copy(update={'mode':'simulation'})
        if workers: raise HTTPException(409,'Finish the current job before starting an experiment.')
        if not registry.recipes(store,body.mode): raise HTTPException(409,'Discover models first, or select Simulation.')
        if body.mode=='live' and not tracing.client: await tracing.initialize()
        job=str(uuid4())
        store.put('experiments',job,dict(id=job,kind=kind,mode=body.mode,status='running',groups={},runs=[],created_at=now()))
        async def work():
            try: await run_experiment(controller,job,kind,**body.model_dump())
            except asyncio.CancelledError: raise
            except Exception as e:
                saved=store.get('experiments',job)
                saved.update(status='failed',error=str(e) if isinstance(e,ValueError) else 'Experiment could not complete safely')
                store.put('experiments',job,saved)
        spawn(work())
        return {'job_id':job}

    @app.post('/api/calibration',status_code=202)
    async def calibrate(body:ExperimentRequest): return await start_experiment('calibration',body)

    @app.post('/api/benchmark',status_code=202)
    async def benchmark(body:ExperimentRequest): return await start_experiment('benchmark',body)

    return app


app=create_app()
