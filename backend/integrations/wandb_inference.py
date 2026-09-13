import asyncio
import time
import httpx
from backend.app.config import credential
from backend.app.pricing import upper_cost, token_cost
from backend.app.schemas import ExecutionResult, now
from backend.app.spend_guard import GuardError

BASE_URL='https://api.inference.wandb.ai/v1'


class WandbInference:
    def __init__(self, settings):
        self.settings=settings

    def headers(self):
        key=credential(self.settings)
        if not key: raise GuardError('W&B authentication required. Complete the secure W&B login, then verify connections.')
        return {'Authorization':f'Bearer {key}','OpenAI-Project':self.settings.project_id}

    async def discover(self):
        async with httpx.AsyncClient(timeout=15) as client:
            response=await client.get(f'{BASE_URL}/models',headers=self.headers())
        if response.status_code != 200:
            raise GuardError(f'W&B model discovery returned HTTP {response.status_code}. Check inference access and billing.')
        return [dict(id=x['id'],verified_at=now()) for x in response.json().get('data',[]) if isinstance(x.get('id'),str)]

    async def complete(self, recipe, model, messages, guard, purpose='inference'):
        # Resolve authentication before making a monetary reservation.
        headers=self.headers()
        reservation=guard.reserve(upper_cost(model,messages,recipe.max_output_tokens))
        start=time.monotonic()
        result=ExecutionResult(model_id=model.model_id,recipe_id=recipe.recipe_id)
        payload={'model':model.model_id,'messages':messages,'max_tokens':recipe.max_output_tokens,'temperature':0}
        if model.reasoning_support and recipe.reasoning:
            payload['reasoning_effort']=recipe.reasoning
        try:
            async with asyncio.timeout(guard.remaining_seconds):
                async with httpx.AsyncClient(timeout=min(guard.remaining_seconds,60)) as client:
                    response=await client.post(f'{BASE_URL}/chat/completions',headers=headers,json=payload)
            if response.status_code != 200:
                result.error=f'W&B inference HTTP {response.status_code}. '+{401:'Authentication failed.',403:'Inference access denied.',429:'Rate limit reached; no automatic retry.'}.get(response.status_code,'Provider request failed.')
            else:
                body=response.json()
                usage=body.get('usage') or {}
                choice=body['choices'][0]
                result.output=choice['message'].get('content') or ''
                result.input_tokens=int(usage.get('prompt_tokens',0))
                result.output_tokens=int(usage.get('completion_tokens',0))
                result.total_tokens=int(usage.get('total_tokens',result.input_tokens+result.output_tokens))
                if 'prompt_tokens' in usage and 'completion_tokens' in usage:
                    result.cost_usd=token_cost(model,result.input_tokens,result.output_tokens)
                result.provider_metadata={'response_id':body.get('id'),'finish_reason':choice.get('finish_reason'),'purpose':purpose,
                    'pricing':'Token usage × documented uncached list rates','usage':usage}
                if not result.output: result.error='The model returned no final output within the token budget.'
        except (TimeoutError,httpx.TimeoutException):
            result.error='Inference deadline exceeded; uncertain spend reservation retained.'
        except (httpx.HTTPError,ValueError,KeyError,IndexError,TypeError):
            result.error='W&B response unavailable or malformed; uncertain spend reservation retained.'
        except asyncio.CancelledError:
            guard.settle(reservation,None)
            raise
        finally:
            result.latency_seconds=time.monotonic()-start
            result.ended_at=now()
        guard.settle(reservation,result.cost_usd)
        return result
