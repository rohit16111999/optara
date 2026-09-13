import asyncio
import httpx
from backend.app.config import credential
from backend.app.schemas import now


async def verify_project(settings):
    key=credential(settings)
    if not key: return {'available':False,'detail':'W&B authentication required'}
    query='query($entity: String!, $project: String!) { viewer { username } project(name:$project, entityName:$entity) { name } }'
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response=await client.post('https://api.wandb.ai/graphql',auth=('api',key),json={'query':query,'variables':{'entity':settings.wandb_entity,'project':settings.wandb_project}})
        body=response.json()
        ok=response.status_code==200 and bool(body.get('data',{}).get('project'))
        return {'available':ok,'detail':'Project access verified' if ok else 'Project unavailable or not created yet','checked_at':now()}
    except Exception: return {'available':False,'detail':'W&B project verification unavailable','checked_at':now()}


async def verify_mcp(settings):
    key=credential(settings)
    if not key: return {'available':False,'detail':'Configured W&B MCP requires WANDB_API_KEY','checked_at':now()}
    # Public MCP client, independent of the live inference path; no guessed tools.
    async def check():
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
        async with streamablehttp_client(settings.wandb_mcp_url,headers={'Authorization':f'Bearer {key}'}) as (read,write,_):
            async with ClientSession(read,write) as session:
                await session.initialize()
                listed=await session.list_tools()
                return {'available':True,'detail':f'{len(listed.tools)} W&B control-plane tools discovered','tools':[t.name for t in listed.tools],'checked_at':now()}
    try: return await asyncio.wait_for(check(),15)
    except Exception: return {'available':False,'detail':'W&B MCP authentication/network unavailable','checked_at':now()}


async def sync_history(integration,store):
    if not integration.client: return {'available':False,'detail':'Initialize Weave first'}
    try:
        rows=await asyncio.wait_for(asyncio.to_thread(lambda:list(integration.client.get_calls(limit=25,columns=['id','display_name','started_at','summary']))),15)
        evidence=[{'id':r.id,'name':r.display_name,'started_at':str(r.started_at),'summary':dict(r.summary or {})} for r in rows]
        store.put('integration','history',{'available':True,'count':len(evidence),'checked_at':now(),'calls':evidence})
        return {'available':True,'count':len(evidence),'checked_at':now()}
    except Exception: return {'available':False,'detail':'Weave history query unavailable'}
