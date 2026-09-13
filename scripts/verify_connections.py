"""Read-only W&B MCP evidence checks plus Optara MCP protocol verification."""
import asyncio
import json
import sys
from pathlib import Path
from backend.app.config import Settings, credential, ROOT
from backend.app.persistence import Store
from backend.app.schemas import now
from backend.integrations.weave_integration import redact


async def main():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.client.stdio import stdio_client
    settings=Settings()
    key=credential(settings)
    if not key: raise SystemExit('Secure W&B sign-in required.')
    proof={'checked_at':now(),'project':settings.project_id,'checks':{}}
    async with streamablehttp_client(settings.wandb_mcp_url,headers={'Authorization':f'Bearer {key}'}) as (read,write,_):
        async with ClientSession(read,write) as session:
            await session.initialize()
            names={t.name for t in (await session.list_tools()).tools}
            queries=[('query_wandb_entity_projects',{'entity':settings.wandb_entity,'max_projects':10}),
                ('infer_trace_schema_tool',{'entity_name':settings.wandb_entity,'project_name':settings.wandb_project,'sample_size':5}),
                ('count_weave_traces_tool',{'entity_name':settings.wandb_entity,'project_name':settings.wandb_project}),
                ('query_weave_traces_tool',{'entity_name':settings.wandb_entity,'project_name':settings.wandb_project,'limit':3,'columns':['id','op_name','started_at','ended_at'],'include_feedback':False,'include_costs':False})]
            for name,arguments in queries:
                if name not in names: raise RuntimeError(f'Required read-only tool unavailable: {name}')
                response=await session.call_tool(name,arguments)
                safe=redact([c.text for c in response.content if c.type=='text'],key)
                proof['checks'][name]={'ok':not response.isError,'result':safe}
                print(name, 'PASS' if not response.isError else 'FAIL')
    params=StdioServerParameters(command=sys.executable,args=['-m','backend.mcp_server.server'],cwd=str(ROOT))
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await session.initialize()
            names=[t.name for t in (await session.list_tools()).tools]
            response=await session.call_tool('get_recent_performance',{'simulation':False})
            proof['checks']['optara_mcp']={'ok':len(names)==5 and not response.isError,'tools':names}
            await asyncio.sleep(2)
            print('optara_mcp', 'PASS' if proof['checks']['optara_mcp']['ok'] else 'FAIL')
    Store(settings.optara_db_path).put('verification','connections',proof)
    (ROOT/'.runtime/connection-proof.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    if not all(c['ok'] for c in proof['checks'].values()): raise SystemExit(1)


if __name__=='__main__': asyncio.run(main())
