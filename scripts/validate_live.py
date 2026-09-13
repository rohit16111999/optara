"""Five bounded real task/shadow pairs, cache, and evidence-gate validation."""
import asyncio
import json
from pathlib import Path
import httpx
from backend.app.config import ROOT


async def finished(client,run_id):
    for _ in range(240):
        run=(await client.get(f'/api/runs/{run_id}')).json()
        events=(await client.get(f'/api/runs/{run_id}/event-history')).json()
        if any(e['stage']=='done' for e in events): return run
        await asyncio.sleep(.5)
    raise RuntimeError('Run completion timed out')


async def main():
    proof={'pairs':[],'cache':False,'gate_checked':False}
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000',timeout=60) as client:
        for index in range(5):
            payload=dict(prompt=f'Calculate {31+index} * 13. Return only the number.',quality_target=.9,max_budget_usd=.003,max_latency_seconds=45,mode='live',bypass_cache=True)
            response=await client.post('/api/runs',json=payload);response.raise_for_status()
            run=await finished(client,response.json()['run_id'])
            assert run['status']=='completed' and run['sla_hit'] and run['trace_url'],run.get('error')
            response=await client.post(f"/api/runs/{run['run_id']}/shadow",json={})
            assert response.status_code in (202,409)
            for _ in range(240):
                pairs=(await client.get('/api/shadow?mode=live')).json()
                pair=next((p for p in pairs if p['production_run']==run['run_id']),None)
                if pair and pair['status']!='running' and ('evaluation_url' in pair or 'trace_status' in pair):break
                await asyncio.sleep(.5)
            assert pair and pair['status']=='completed'
            after=(await client.get(f"/api/runs/{run['run_id']}")).json()
            assert all(run[k]==after[k] for k in ['output','quality','total_cost','total_latency','sla_hit'])
            proof['pairs'].append(pair)
            print(f"Pair {index+1}: production {run['quality']}, shadow {pair['shadow_quality']}; production immutable",flush=True)
            if index==0:
                rejected=await client.post(f"/api/policies/{pair['policy_id']}/promote",json={})
                assert rejected.status_code==409
                proof['gate_checked']=True
        payload['bypass_cache']=False
        for _ in range(3):
            response=await client.post('/api/runs',json=payload);response.raise_for_status()
            cached=await finished(client,response.json()['run_id'])
            if cached['cache_hit']:
                assert cached['total_cost']==0 and not cached['executions']
                proof['cache']=True;proof['cache_run']=cached['run_id'];break
        assert proof['cache']
        proof['policies']=(await client.get('/api/policies?mode=live')).json()
    (ROOT/'.runtime/live-validation.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print('Live repair evidence retained from browser run; cache, five shadow pairs, immutability and premature promotion rejection passed.')


if __name__=='__main__':asyncio.run(main())
