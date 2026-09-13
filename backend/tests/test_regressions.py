import pytest
from backend.app.schemas import TaskRequest,Recipe
from backend.app.safe_python import Interpreter,UnsupportedCode
from backend.app import registry,history
from benchmarks.runner import baseline_recipes


def test_augmented_assignment_cannot_allocate_unbounded_memory():
    with pytest.raises(UnsupportedCode,match='Allocation limit'):
        Interpreter().run('def f():\n    a = "x"\n    a *= 1000000000\n    return a','f',[])


async def test_dry_run_configuration_forces_simulation(controller):
    controller.settings.dry_run_mode=True
    result=await controller.run(TaskRequest(prompt='Reply with exactly: DRY_RUN_OK'))
    assert result.task.mode=='simulation' and result.output=='DRY_RUN_OK'
    assert result.trace_url is None


async def test_explicit_cache_bypass(controller):
    first=await controller.run(TaskRequest(prompt='Reply with exactly: CACHE_TEST',mode='simulation'))
    second=await controller.run(TaskRequest(prompt='Reply with exactly: CACHE_TEST',mode='simulation',bypass_cache=True))
    assert not first.cache_hit and not second.cache_hit and second.executions


def test_verification_recipe_excluded_from_product_registry(store):
    registry.register_models(store,[{'id':'meta-llama/Llama-3.1-8B-Instruct'}])
    store.put('recipes','auth',Recipe(recipe_id='auth',model_id='meta-llama/Llama-3.1-8B-Instruct',name='Verification',max_output_tokens=32,metadata={'verification_only':True}))
    assert all(r.recipe_id!='auth' for r in registry.recipes(store))


def test_cheap_baseline_uses_observed_whole_recipe_cost(store):
    recipes=registry.recipes(store,'simulation')
    for r,cost in zip(recipes,[.02,.01,.03]):history.observe(store,'simulation','math',r.recipe_id,.9,cost,2,r.recipe_id,'calibration')
    cheap,_=baseline_recipes(store,'simulation',recipes)
    assert cheap.recipe_id=='simulation-deliberate-v1'


def test_bounded_comprehensions_support_real_model_output():
    code='def sum_even(nums):\n    return sum(x for x in nums if isinstance(x, int) and x % 2 == 0)'
    assert Interpreter().run(code,'sum_even',[[1,2,4,-6,3]])==0
    assert Interpreter().run('def f(nums):\n    return [x*2 for x in nums if x>0]','f',[[-1,2,3]])==[4,6]
    with pytest.raises(UnsupportedCode):
        Interpreter().run('def f():\n    return [x for x in range(10000) for y in range(10000)]','f',[])


def test_evaluator_limitation_is_not_certified_as_incorrect_code():
    from backend.app.evaluator import deterministic_evaluate
    from backend.app.profiler import profile_task
    task=TaskRequest(prompt='Implement a Python function',evaluation_spec={'type':'python','function':'f','tests':[{'args':[],'expected':1}]})
    result=deterministic_evaluate(task,profile_task(task),'def f():\n    import math\n    return 1')
    assert not result.passed and result.confidence==0 and not result.deterministic
    assert result.evaluation_type=='python_evaluator_limitation'


def test_historical_evaluator_versions_do_not_mix(store):
    r=registry.recipes(store,'simulation')[0]
    store.put('observations','old',dict(mode='simulation',family='math',recipe_id=r.recipe_id,quality=0,cost=1,latency=100,evaluator_version='v1'))
    assert history.expected(store,'simulation','math',r,.01).observations==0


def test_experiment_pool_limits_adaptive_scheduler(store,settings):
    from backend.app.scheduler import schedule
    from backend.app.profiler import profile_task
    task=TaskRequest(prompt='Calculate 1+1',mode='simulation',max_latency_seconds=30)
    selected,*_=schedule(store,settings,task,profile_task(task),allowed_recipes=['simulation-verified-v1'])
    assert selected.recipe_id=='simulation-verified-v1'


async def test_forced_dry_experiment_keeps_simulation_namespace(controller):
    from benchmarks.runner import run_experiment
    controller.settings.dry_run_mode=True
    result=await run_experiment(controller,'dry-report','calibration','live',max_models=1,task_count=1)
    assert result['mode']=='simulation'
    assert all(o['mode']=='simulation' for o in controller.store.list('observations'))
