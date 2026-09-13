import asyncio
import json
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from pydantic import ValidationError
from backend.app.schemas import TaskRequest,ExpectedMetrics,Candidate,Recipe,ModelSpec
from backend.app.profiler import profile_task
from backend.app.pareto import dominates,frontier
from backend.app.scheduler import schedule
from backend.app import registry,history,cache,policy
from backend.app.pricing import token_cost,upper_cost
from backend.app.spend_guard import SpendGuard,GuardError
from backend.app.evaluator import deterministic_evaluate
from backend.app.safe_python import Interpreter,UnsupportedCode
from backend.app.controller import sla
from backend.app.shadow import should_shadow,execute_shadow
from backend.integrations.weave_integration import redact
from benchmarks.runner import run_experiment


def task(**kwargs): return TaskRequest(prompt='Calculate 17 * 23. Return only the number.',mode='simulation',**kwargs)
def recipe(id='r'): return Recipe(recipe_id=id,model_id='m',name=id,max_output_tokens=384)
def candidate(id,q,c,l,n=20,u=.02): return Candidate(recipe=recipe(id),metrics=ExpectedMetrics(expected_quality=q,expected_cost=c,expected_latency=l,observations=n,uncertainty=u))


@pytest.mark.parametrize('fields',[{'prompt':''},{'prompt':'  '},{'quality_target':1.01},{'max_budget_usd':0},{'max_budget_usd':-1},{'max_latency_seconds':0},{'max_latency_seconds':181},{'quality_target':float('nan')}])
def test_request_validation(fields):
    with pytest.raises(ValidationError): TaskRequest(**{'prompt':'task',**fields})


def test_schema_remote_reference_rejected():
    with pytest.raises(ValidationError): TaskRequest(prompt='JSON',evaluation_spec={'schema':{'$ref':'https://example.com/schema'}})


@pytest.mark.parametrize('prompt,family',[('Implement a Python function','coding'),('Extract invoice fields','extraction'),('Calculate 3 + 4','math'),('Summarize this paragraph','summarization'),('Classify sentiment','classification'),('Write a story','writing')])
def test_profiler(prompt,family): assert profile_task(TaskRequest(prompt=prompt)).task_family==family


@pytest.mark.parametrize('prompt',['Current weather in Seattle','Latest stock price','My account balance today','News now'])
def test_freshness_bypasses_cache(prompt): assert not profile_task(TaskRequest(prompt=prompt)).cacheable


def test_pareto_strict_and_equal():
    a=candidate('a',.9,.01,2); b=candidate('b',.8,.02,3); equal=candidate('equal',.9,.01,2)
    assert dominates(a.metrics,b.metrics)
    assert not dominates(a.metrics,equal.metrics)
    assert {c.recipe.recipe_id for c in frontier([a,b,equal])}=={'a','equal'}


def test_pareto_tradeoff_and_unknown():
    a=candidate('a',.9,.02,2); b=candidate('b',.8,.01,3); missing=candidate('unknown',1,None,1)
    assert len(frontier([a,b,missing]))==3


def test_pareto_permutation_invariance():
    import itertools
    points=[candidate('a',.9,.01,2),candidate('b',.9,.02,2),candidate('c',.95,.03,4)]
    for values in itertools.permutations(points): assert {v.recipe.recipe_id for v in frontier(values)}=={'a','c'}


def test_scheduler_confident_minimum_cost(monkeypatch,store,settings):
    available=[recipe('a'),recipe('b'),recipe('c')]
    monkeypatch.setattr(registry,'recipes',lambda *_:available)
    monkeypatch.setattr(registry,'models',lambda *_:[ModelSpec(model_id='m',input_price_per_million=1,output_price_per_million=1)])
    metrics={'a':candidate('a',.97,.005,2).metrics,'b':candidate('b',.99,.015,1).metrics,'c':candidate('c',.7,.001,1).metrics}
    monkeypatch.setattr('backend.app.scheduler.expected',lambda _,mode,family,r,bound:metrics[r.recipe_id])
    t=task(); selected,top,_,reason,_=schedule(store,settings,t,profile_task(t))
    assert selected.recipe_id=='a' and len(top)==3 and '20 observations' in reason


def test_scheduler_uncertainty_risk(store,settings):
    t=task(); _,top,_,reason,_=schedule(store,settings,t,profile_task(t))
    assert len(top)==3 and 'SLA risk' in reason and 'uncalibrated' in reason


def test_scheduler_no_feasible(store,settings):
    t=task(max_latency_seconds=1)
    with pytest.raises(GuardError,match='No budget-and-deadline'): schedule(store,settings,t,profile_task(t))


def test_registry_uses_only_discovered_models(store):
    registry.register_models(store,[{'id':'meta-llama/Llama-3.1-8B-Instruct','verified_at':'2026-09-13'}])
    assert len(registry.recipes(store))==3
    registry.register_models(store,[{'id':'unknown/real-discovered-model'}])
    assert len(registry.recipes(store))==0
    assert registry.models(store)[0].output_price_per_million is None


def test_cost_counts_and_unknown():
    m=ModelSpec(model_id='m',input_price_per_million=.2,output_price_per_million=.4)
    assert token_cost(m,1000,500)==pytest.approx(.0004)
    assert token_cost(ModelSpec(model_id='unknown'),10,10) is None
    assert upper_cost(m,[{'content':'é'}],32)>token_cost(m,1,32)


def test_spend_guard_call_cap(store,settings):
    guard=SpendGuard(store,settings,task())
    for _ in range(settings.max_model_calls_per_request): guard.reserve(0)
    with pytest.raises(GuardError,match='Maximum model calls'): guard.reserve(0)


def test_spend_guard_unknown_and_budget(store,settings):
    t=TaskRequest(prompt='test',max_budget_usd=.001)
    g=SpendGuard(store,settings,t)
    with pytest.raises(GuardError,match='Cost unavailable'): g.reserve(None)
    with pytest.raises(GuardError,match='Request budget'): g.reserve(.002)
    token=g.reserve(.0008); g.settle(token,.0002)
    assert g.reserved==pytest.approx(.0002)
    assert store.spend_total()==pytest.approx(.0002)


def test_spend_timeout_reservation_retained(store,settings):
    g=SpendGuard(store,settings,TaskRequest(prompt='test'))
    token=g.reserve(.001);g.settle(token,None)
    assert store.spend_total()==.001


def test_spend_deadline(store,settings):
    g=SpendGuard(store,settings,task());g.deadline=0
    with pytest.raises(GuardError,match='deadline'):g.reserve(0)


def test_concurrent_global_budget_atomic(store,settings):
    settings.max_total_dev_spend=.015
    def call(_):
        try: SpendGuard(store,settings,TaskRequest(prompt='test')).reserve(.01);return True
        except GuardError:return False
    with ThreadPoolExecutor(max_workers=3) as pool: successes=list(pool.map(call,range(3)))
    assert sum(successes)==1 and store.spend_total()==.01


def test_shadow_budget_separate(store,settings):
    settings.max_shadow_spend=.005
    with pytest.raises(GuardError,match='Shadow spend'):SpendGuard(store,settings,TaskRequest(prompt='test'),scope='shadow').reserve(.006)
    assert store.spend_total()==0


def test_experiment_batch_budget(store,settings):
    SpendGuard(store,settings,TaskRequest(prompt='test'),scope='benchmark',batch_id='batch',batch_limit=.015).reserve(.01)
    with pytest.raises(GuardError,match='Experiment budget'): SpendGuard(store,settings,TaskRequest(prompt='test'),scope='benchmark',batch_id='batch',batch_limit=.015).reserve(.01)


def test_exact_evaluator():
    t=task();p=profile_task(t)
    assert deterministic_evaluate(t,p,'391').score==1
    assert deterministic_evaluate(t,p,'390').score==0


def test_structural_json_not_semantic_quality():
    t=TaskRequest(prompt='Extract important fields into JSON')
    assert deterministic_evaluate(t,profile_task(t),'{}') is None


def test_json_reference():
    t=TaskRequest(prompt='Extract JSON',evaluation_spec={'type':'json','schema':{'type':'object','required':['name'],'properties':{'name':{'type':'string'}}},'expected':{'name':'Ada'}})
    assert deterministic_evaluate(t,profile_task(t),'{"name":"Ada"}').passed
    assert not deterministic_evaluate(t,profile_task(t),'{"name":17}').passed
    assert not deterministic_evaluate(t,profile_task(t),'{"name":"Alan"}').passed
    assert not deterministic_evaluate(t,profile_task(t),'{"name":').passed


def test_supported_python_executes_without_exec():
    code='def add(a, b):\n    return a + b'
    assert Interpreter().run(code,'add',[2,3])==5


@pytest.mark.parametrize('code',[
    'import os\ndef f():\n    return 1',
    'def f():\n    return __import__("os").getcwd()',
    'def f():\n    return (1).__class__',
    'def f():\n    while True:\n        pass',
    'def f():\n    return "x" * 1000000000',
    'def f():\n    return f()',
])
def test_unsafe_python_blocked(code):
    with pytest.raises(UnsupportedCode): Interpreter().run(code,'f',[])


@pytest.mark.parametrize('quality,cost,latency,hit',[(.9,.01,2,True),(.8,.01,2,False),(.9,.03,2,False),(.9,.01,60,False),(.9,None,2,False)])
def test_sla_all_three(quality,cost,latency,hit): assert sla(quality,cost,latency,task())[0] is hit


def test_cache_key_semantic_safety():
    r=recipe();a=TaskRequest(prompt='Return "Ada"');b=TaskRequest(prompt='Return "ada"')
    assert cache.cache_key(a,r)!=cache.cache_key(b,r)
    assert cache.cache_key(a,r)!=cache.cache_key(a,r.model_copy(update={'version':2}))
    assert cache.cache_key(a,r)!=cache.cache_key(a.model_copy(update={'quality_target':.95}),r)


def test_history_prior_and_mode_isolation(store):
    r=recipe();history.observe(store,'live','coding','r',1,.01,2,'a','live')
    m=history.expected(store,'live','coding',r,.02)
    assert m.expected_quality==pytest.approx(2/3) and m.observations==1
    assert history.expected(store,'simulation','coding',r,.02).observations==0


def test_shadow_sampling():
    assert not should_shadow('abc',0)
    assert should_shadow('abc',1)
    assert should_shadow('abc',.1)==should_shadow('abc',.1)
    assert 50<sum(should_shadow(str(i),.08) for i in range(1000))<120


def pair(i=0,**extra):
    return dict(id=str(i),production_run=str(i),mode='live',family='coding',shadow_recipe='r',production_recipe='base',status='completed',production_quality=.95,shadow_quality=.96,production_cost=.02,shadow_cost=.01,production_latency=3,shadow_latency=2,production_sla=True,shadow_sla=True,**extra)


def test_policy_requires_evidence():
    assert not policy.assess([pair()],5)[0]
    assert policy.assess([pair(i) for i in range(5)],5)[0]
    bad=[{**pair(i),'shadow_quality':.7} for i in range(5)]
    assert not policy.assess(bad,5)[0]


def test_policy_version_and_promotion(store,settings):
    store.put('shadow','0',pair())
    p=policy.update_policy(store,settings,'live','coding','r')
    assert p.version==1 and p.status=='shadow'
    with pytest.raises(ValueError): policy.promote(store,settings,p.policy_id)
    for i in range(1,5):store.put('shadow',str(i),pair(i))
    promoted=policy.promote(store,settings,p.policy_id)
    assert promoted.status=='production' and promoted.evidence_count==5
    next_policy=policy.update_policy(store,settings,'live','coding','other')
    assert next_policy.version==2


def test_policy_duplicate_task_does_not_inflate(store,settings):
    for i in range(7):store.put('shadow',str(i),{**pair(i),'production_run':'same'})
    p=policy.update_policy(store,settings,'live','coding','r')
    assert p.evidence_count==1 and not p.comparison['eligible']


async def test_complete_flow_and_cache(controller):
    t=task();first=await controller.run(t)
    assert first.status=='completed' and first.output=='391' and first.sla_hit
    second=await controller.run(task())
    assert second.cache_hit and second.executions==[] and second.total_cost==0
    assert len(controller.store.list('observations'))==1
    assert first.trace_url is None and 'simulation' in first.trace_status


async def test_targeted_repair_bounded(controller):
    t=TaskRequest(prompt='JSON repair demo. Extract Ada age 36.',mode='simulation',evaluation_spec={'type':'json','schema':{'type':'object','required':['name','age']},'expected':{'name':'Ada','age':36}})
    run=await controller.run(t)
    assert run.status=='completed' and len(run.repair_steps)==1 and run.quality==1
    assert len(run.executions)<=controller.settings.max_model_calls_per_request
    stages=controller.store.events(run.run_id)
    assert any(e['stage']=='repair' and e['status']=='active' for e in stages)


async def test_no_unlimited_repair(controller):
    run=await controller.run(TaskRequest(prompt='Write an original research proposal',mode='simulation'))
    assert not run.sla_hit and len(run.repair_steps)==1 and len(run.executions)<=5


async def test_shadow_keeps_production_immutable(controller):
    run=await controller.run(task())
    before={k:controller.store.get('runs',run.run_id)[k] for k in ['output','quality','total_cost','total_latency','sla_hit']}
    shadow=await execute_shadow(controller,run)
    after=controller.store.get('runs',run.run_id)
    assert shadow['status']=='completed'
    assert before=={k:after[k] for k in before}
    duplicate=await execute_shadow(controller,run)
    assert duplicate['shadow_run']==shadow['shadow_run']
    assert len(controller.store.list('shadow'))==1


async def test_calibration_and_three_baselines(controller):
    calibration=await run_experiment(controller,str(uuid4()),'calibration','simulation',max_models=1,max_cost=.01,task_count=1)
    assert calibration['status']=='completed' and len(calibration['groups'])==3
    benchmark=await run_experiment(controller,str(uuid4()),'benchmark','simulation',max_models=1,max_cost=.01,task_count=1)
    assert set(benchmark['groups'])=={'Always Strong','Always Cheap','Optara'}
    assert all(g['tasks']==1 for g in benchmark['groups'].values())


async def test_missing_credentials_safe_failure(controller,monkeypatch):
    monkeypatch.setattr('backend.integrations.wandb_inference.credential',lambda _:None)
    with pytest.raises(GuardError,match='authentication'): await controller.engine.provider.discover()
    run=await controller.run(TaskRequest(prompt='Reply with exactly: OK'))
    assert run.status=='failed' and not run.executions and not run.sla_hit


def test_redaction():
    assert redact({'Authorization':'secret','nested':{'api_key':'hidden'},'text':'contains credential'},'credential')=={'Authorization':'[REDACTED]','nested':{'api_key':'[REDACTED]'},'text':'contains [REDACTED]'}
