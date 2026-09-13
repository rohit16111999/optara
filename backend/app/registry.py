import hashlib
from .schemas import ModelSpec, Recipe
from .pricing import prices


def register_models(store, discovered):
    pricing = prices()
    discovered_ids = {m['id'] for m in discovered}
    for previous in store.list('models'):
        if previous['model_id'] not in discovered_ids:
            previous['enabled'] = False
            store.put('models', previous['model_id'], previous)
    result = []
    for item in discovered:
        model_id = item['id']
        rates = pricing['models'].get(model_id, [None,None])
        model = ModelSpec(model_id=model_id,input_price_per_million=rates[0],output_price_per_million=rates[1],
            reasoning_support=model_id.startswith('openai/gpt-oss'),last_verified=item.get('verified_at'),
            metadata={'pricing_source':pricing['source'],'pricing_verified_at':pricing['verified_at'],'discovery':'authenticated models API'})
        store.put('models', model_id, model)
        result.append(model)
    # Curated budget-safe pool from real discovery, at most three models.
    pool = sorted([m for m in result if m.input_price_per_million is not None], key=lambda m:m.output_price_per_million)[:3]
    for model in pool:
        prefix = hashlib.sha256(model.model_id.encode()).hexdigest()[:8]
        for suffix, name, tokens, verify in [('focused','Focused',384,False),('deliberate','Deliberate',1024,False),('verified','Verified',1024,True)]:
            recipe = Recipe(recipe_id=f'{prefix}-{suffix}-v2',model_id=model.model_id,name=name,version=2,
                reasoning='low' if model.reasoning_support and suffix=='focused' else ('medium' if model.reasoning_support else None),
                max_output_tokens=tokens,verifier_enabled=verify,verifier_model=model.model_id if verify else None,
                agents=2 if verify else 1,metadata={'version_source':'optara-v2'})
            store.put('recipes',recipe.recipe_id,recipe)
    return result


def models(store, mode='live'):
    if mode=='simulation':
        return [ModelSpec(model_id='simulation/local',provider='Local fixtures · SIMULATION',input_price_per_million=0,output_price_per_million=0)]
    return [ModelSpec(**m) for m in store.list('models') if m['enabled']]


def recipes(store, mode='live'):
    if mode=='simulation':
        return [Recipe(recipe_id=f'simulation-{s}-v1',model_id='simulation/local',name=name,max_output_tokens=tokens,
            verifier_enabled=v,verifier_model='simulation/local' if v else None,agents=2 if v else 1)
            for s,name,tokens,v in [('focused','Focused',384,False),('deliberate','Deliberate',1024,False),('verified','Verified',1024,True)]]
    enabled = {m.model_id for m in models(store)}
    rows=[Recipe(**r) for r in store.list('recipes') if r['model_id'] in enabled and r.get('metadata',{}).get('version_source')=='optara-v2' and not r.get('metadata',{}).get('verification_only')]
    specs={m.model_id:m for m in models(store)}
    return sorted(rows,key=lambda r:(specs[r.model_id].output_price_per_million,r.model_id,r.max_output_tokens,r.verifier_enabled))
