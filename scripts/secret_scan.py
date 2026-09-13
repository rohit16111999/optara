"""Scan source and local evidence without ever printing a matched secret."""
import json
import os
import re
from pathlib import Path
from backend.app.config import ROOT,Settings,credential


def main():
    key=credential(Settings())
    known=key.encode() if key else None
    excluded={'.git','.venv','node_modules','.next','__pycache__','.pytest_cache','uv-cache','npm-cache'}
    source_suffixes={'.py','.ts','.tsx','.js','.mjs','.json','.toml','.md','.ps1','.css','.txt','.log','.env'}
    token=re.compile(rb'\b(?:wandb_v1_|sk-proj-)[A-Za-z0-9_-]{25,}')
    assignment=re.compile(rb'(?i)(?:api_key|password|access_token)\s*[=:]\s*[\x22\x27]([A-Za-z0-9_-]{32,})[\x22\x27]')
    findings=[];count=0
    for folder,dirs,files in os.walk(ROOT):
        dirs[:]=[d for d in dirs if d not in excluded]
        for name in files:
            path=Path(folder)/name
            if path.stat().st_size>50_000_000:continue
            content=path.read_bytes();count+=1
            reasons=[]
            if known and known in content:reasons.append('Known W&B credential detected')
            if path.suffix in source_suffixes or name.startswith('.env'):
                if token.search(content) or assignment.search(content):reasons.append('Credential-shaped literal detected')
            if reasons:findings.append({'file':str(path.relative_to(ROOT)),'reasons':reasons})
    report={'files_scanned':count,'findings':findings,'passed':not findings,'scope':'Project source and local evidence; dependency caches/builds excluded. Matched values never emitted.'}
    (ROOT/'.runtime').mkdir(exist_ok=True)
    (ROOT/'.runtime/secret-scan.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if findings:raise SystemExit(1)


if __name__=='__main__':main()
