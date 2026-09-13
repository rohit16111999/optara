import argparse
import asyncio
import json
import httpx


async def main(kind):
    parser=argparse.ArgumentParser(description=f'Cost-bounded Optara {kind}; backend must be running.')
    parser.add_argument('--dry-run',action='store_true',help='Use isolated local SIMULATION fixtures; never call W&B')
    parser.add_argument('--max-models',type=int,default=2)
    parser.add_argument('--max-cost',type=float,default=.03)
    parser.add_argument('--tasks',type=int,default=3)
    args=parser.parse_args()
    mode='simulation' if args.dry_run else 'live'
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000',timeout=60) as client:
        if mode=='live':
            verify=await client.post('/api/status/verify',json={})
            if not verify.json().get('discovery',{}).get('available'):
                raise SystemExit('W&B discovery unavailable. Complete secure W&B login before real experiments.')
        response=await client.post(f'/api/{kind}',json={'mode':mode,'max_models':args.max_models,'max_cost':args.max_cost,'task_count':args.tasks})
        if response.status_code!=202: raise SystemExit(response.json().get('detail','Experiment request failed'))
        id=response.json()['job_id']
        print(f'{kind.title()} {id} started · {mode.upper()} · ${args.max_cost:.3f} cap')
        for _ in range(1200):
            reports=(await client.get('/api/experiments',params={'mode':mode})).json()
            report=next((r for r in reports if r['id']==id),None)
            if report and report['status']!='running':
                print(json.dumps(report,indent=2));return 0 if report['status']=='completed' else 1
            await asyncio.sleep(.5)
        raise SystemExit('Polling timeout. The persisted experiment remains available in the UI.')
