import argparse
import json
from pathlib import Path
from backend.app.config import Settings
from backend.app.persistence import Store
from backend.app.schemas import now
from backend.app.evaluator import VERSION


def main():
    parser=argparse.ArgumentParser(description='Export safe, mode-separated experiment evidence for marimo/Molab or ARIA review.')
    parser.add_argument('--mode',choices=['live','simulation'],default='live')
    parser.add_argument('--output',type=Path,default=Path('data/evidence.json'))
    args=parser.parse_args()
    store=Store(Settings().optara_db_path)
    evidence={'mode':args.mode,'exported_at':now(),'observations':[],'policies':[],'shadow':[],'experiments':[],'runs':[]}
    for collection in ['observations','policies','shadow','experiments']:
        evidence[collection]=[row for row in store.list(collection,10000) if row.get('mode')==args.mode]
    evidence['evaluator_version']=VERSION
    evidence['observations']=[o for o in evidence['observations'] if o.get('evaluator_version','v1')==VERSION]
    for run in store.list('runs',10000):
        if run['task']['mode']==args.mode:
            evidence['runs'].append({k:run.get(k) for k in ['run_id','status','quality','total_cost','total_latency','sla_hit','cache_hit','trace_url','scheduler_reason','selected_recipe','profile']})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    print(f'Exported {len(evidence["runs"])} {args.mode} run summaries to {args.output}. Prompts, outputs and credentials excluded.')


if __name__=='__main__':main()
