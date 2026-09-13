"""Single inference entry point; simulation fixtures are isolated and explicit."""
import asyncio
import json
import re
import time
from .schemas import ExecutionResult, now


class InferenceEngine:
    def __init__(self,provider): self.provider=provider

    async def execute(self,task,recipe,model,messages,guard,purpose='inference'):
        if task.mode=='live': return await self.provider.complete(recipe,model,messages,guard,purpose)
        guard.reserve(0)
        started=time.monotonic()
        # Deliberate fixture pacing is only enabled in explicitly labelled Simulation.
        await asyncio.sleep(min(.18,guard.remaining_seconds))
        prompt=task.prompt.lower()
        if purpose=='judge':
            output=json.dumps({'score':.5,'confidence':.4,'explanation':'Simulation rubric fixture; this is not measured model quality.'})
        elif purpose=='verifier':
            output='Simulation verifier fixture: review task constraints and edge cases.'
        elif 'longest consecutive' in prompt:
            output='```python\ndef longest_consecutive(nums):\n    values = set(nums)\n    best = 0\n    for value in values:\n        if value - 1 not in values:\n            end = value\n            while end in values:\n                end += 1\n            best = max(best, end - value)\n    return best\n```\nTime: O(n). Space: O(n).'
        elif 'sum_even' in prompt:
            output='```python\ndef sum_even(nums):\n    total = 0\n    for n in nums:\n        if n % 2 == 0:\n            total += n\n    return total\n```'
        elif 'json' in prompt:
            if 'repair demo' in prompt and purpose!='repair': output='{"name": "Ada", "age": 36'
            else: output=json.dumps({'name':'Ada','age':36})
        elif task.evaluation_spec.get('expected') is not None:
            output=str(task.evaluation_spec['expected'])
        elif 'reply with exactly' in prompt:
            output=re.split(r'reply with exactly\s*:?\s*',task.prompt,flags=re.I)[-1].strip()
        else:
            match=re.search(r'(\d+)\s*([+*×])\s*(\d+)',prompt)
            if match:
                a,op,b=match.groups()
                output=str(int(a)+int(b) if op=='+' else int(a)*int(b))
            else: output='SIMULATION: This local fixture demonstrates scheduling and evaluation. Select Live W&B for an actual model response to this task.'
        return ExecutionResult(output=output,model_id=model.model_id,recipe_id=recipe.recipe_id,cost_usd=0,
            latency_seconds=time.monotonic()-started,ended_at=now(),provider_metadata={'simulation':True,'purpose':purpose,'usage':'No model tokens consumed'})
