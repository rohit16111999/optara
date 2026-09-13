from . import registry
from .history import expected
from .pareto import dominates
from .pricing import upper_cost
from .schemas import Candidate
from .spend_guard import GuardError


def schedule(store, settings, task, profile, forced_recipe=None,allowed_recipes=None):
    available = registry.recipes(store,task.mode)
    if allowed_recipes is not None: available=[r for r in available if r.recipe_id in allowed_recipes]
    specs = {m.model_id:m for m in registry.models(store,task.mode)}
    if forced_recipe:
        special=store.get('recipes',forced_recipe)
        if special and special.get('metadata',{}).get('verification_only') and special['model_id'] in specs:
            from .schemas import Recipe
            available.append(Recipe(**special))
    if not available:
        raise GuardError('No verified models. Connect W&B and discover models, or explicitly select Simulation.')
    candidates = []
    rejected = []
    for recipe in available:
        bound = upper_cost(specs[recipe.model_id],[{'content':task.prompt}],recipe.max_output_tokens)
        # Recipe includes output evaluation, verifier, and one reserved repair allowance.
        bound = bound * (2 + int(recipe.verifier_enabled) + recipe.repair_limit) if bound is not None else None
        metrics = expected(store,task.mode,profile.task_family,recipe,bound)
        c = Candidate(recipe=recipe,metrics=metrics)
        cap = min(task.max_budget_usd,settings.max_cost_per_request)
        reasons=[]
        if metrics.expected_cost is None: reasons.append('Authoritative cost unavailable')
        elif metrics.expected_cost > cap: reasons.append('Expected cost exceeds budget')
        if metrics.expected_latency > task.max_latency_seconds: reasons.append('Expected latency exceeds deadline')
        c.feasible = not reasons
        if reasons:
            c.rejection_reason = '; '.join(reasons)
            rejected.append(c)
        else:
            candidates.append(c)
    if not candidates:
        raise GuardError('No budget-and-deadline-feasible recipe. Increase constraints or calibrate latency estimates.')
    # Only measured alternatives may eliminate one another; identical cold priors
    # do not prove that token/verification variants are inferior.
    pareto=[]
    for c in candidates:
        dominator = next((d for d in candidates if d is not c and d.metrics.observations and c.metrics.observations and dominates(d.metrics,c.metrics)),None)
        if dominator and not forced_recipe:
            c.rejection_reason=f'Pareto dominated by {dominator.recipe.name} ({dominator.recipe.recipe_id})'
            rejected.append(c)
        else: pareto.append(c)
    confident = lambda c: c.metrics.expected_quality-c.metrics.uncertainty >= task.quality_target
    policies = [p for p in store.list('policies') if p['mode']==task.mode and p['task_family']==profile.task_family and p['status']=='production']
    preferences = policies[0]['recipe_preferences'] if policies else []
    rank = lambda c: (not confident(c), c.metrics.expected_cost if confident(c) else -(c.metrics.expected_quality-c.metrics.uncertainty),
        c.recipe.recipe_id not in preferences,c.metrics.expected_cost,c.metrics.expected_latency,c.recipe.recipe_id)
    pareto.sort(key=rank)
    if forced_recipe:
        chosen = next((c for c in candidates if c.recipe.recipe_id==forced_recipe),None)
        if chosen is None: raise GuardError('The fixed baseline recipe cannot fit this task.')
        pareto.remove(chosen)
        pareto.insert(0,chosen)
    top = pareto[:settings.top_k]
    for c in pareto[settings.top_k:]:
        c.rejection_reason='Outside the top-K live candidate set'
        rejected.append(c)
    selected = top[0]
    selected.selected = True
    for i,c in enumerate(top):
        c.rank=i+1
        if i: c.rejection_reason='Higher cost among confident choices' if confident(selected) else 'Lower conservative quality or less favorable cost/evidence tie-break'
    m=selected.metrics
    if m.observations:
        reason=f'{selected.recipe.name} selected from {len(top)} candidates: smoothed quality {m.expected_quality:.2f} ± {m.uncertainty:.2f}, ${m.expected_cost:.5f} expected cost, {m.expected_latency:.2f}s, {m.observations} observations.'
    else:
        reason=f'{selected.recipe.name} is an uncalibrated exploration choice. No historical quality evidence yet; cost reserve ${m.expected_cost:.5f}. Quality and latency are priors.'
    if not confident(selected): reason+=' SLA risk: no candidate confidently meets the quality target.'
    if forced_recipe: reason='Fixed baseline/experiment selection. '+reason
    return selected.recipe, top, rejected, reason, (policies[0]['version'] if policies else None)
