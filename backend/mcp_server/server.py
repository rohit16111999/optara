"""Optara MCP: HTTP to the existing control plane, avoiding a second DB owner."""
import httpx
from mcp.server.fastmcp import FastMCP

if __name__=='__main__':
    import os
    import contextlib
    import sys
    from backend.app.config import Settings,credential
    from backend.integrations.weave_integration import redact
    settings=Settings()
    key=credential(settings)
    if key:
        # Official Weave MCP auto-instrumentation. Keep protocol stdout clean.
        try:
            import weave
            os.environ['WANDB_API_KEY']=key
            with contextlib.redirect_stdout(sys.stderr):
                trace_client=weave.init(settings.project_id,settings={'print_call_link':False},postprocess_inputs=lambda v:redact(v,key),postprocess_output=lambda v:redact(v,key))
                weave.integrations.patch_fastmcp()
        except Exception:
            print('MCP tracing unavailable; local control-plane tools remain usable.',file=sys.stderr)

mcp=FastMCP('Optara',instructions='Optimize complete execution recipes with quality, spend and deadline constraints. Live optimize_task can spend money under the provided budget. All calls reuse the running Optara control plane and its tracing.',host='127.0.0.1',port=8001)


async def request(method,path,body=None):
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000',timeout=60) as client:
        response=await client.request(method,path,json=body)
    if response.is_error: return {'error':response.json().get('detail','Control plane error')}
    return response.json()


@mcp.tool()
async def optimize_task(prompt:str,quality_target:float=.9,max_budget_usd:float=.02,max_latency_seconds:float=45,simulation:bool=False)->dict:
    """Start a budget-bounded task; returns run_id for retrieving the persisted result. Live mode uses paid inference."""
    return await request('POST','/api/runs',{'prompt':prompt,'quality_target':quality_target,'max_budget_usd':max_budget_usd,'max_latency_seconds':max_latency_seconds,'mode':'simulation' if simulation else 'live'})


@mcp.tool()
async def get_run_result(run_id:str)->dict:
    """Read a persisted task, including schedule reasoning, evaluation, spend and trace URL."""
    return await request('GET',f'/api/runs/{run_id}')


@mcp.tool()
async def explain_recipe(recipe_id:str,simulation:bool=False)->dict:
    """Inspect the full execution recipe and current coding-family empirical estimates."""
    rows=await request('GET',f'/api/recipes?mode={"simulation" if simulation else "live"}')
    if isinstance(rows,dict):return rows
    return next((r for r in rows if r['recipe']['recipe_id']==recipe_id),{'error':'Recipe not found'})


@mcp.tool()
async def get_policy_summary(simulation:bool=False)->list:
    """List candidate, shadow, rejected and production policy versions. Read-only."""
    return await request('GET',f'/api/policies?mode={"simulation" if simulation else "live"}')


@mcp.tool()
async def get_recent_performance(simulation:bool=False)->list:
    """Return the latest 10 actual run records from the selected evidence namespace."""
    return await request('GET',f'/api/runs?limit=10&mode={"simulation" if simulation else "live"}')



if __name__=='__main__':
    try: mcp.run(transport='stdio')
    finally:
        if 'trace_client' in globals(): trace_client.flush()
