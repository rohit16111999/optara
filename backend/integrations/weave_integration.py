"""Explicit public Weave Calls: safe metadata only, no objects holding credentials."""
import asyncio
import os
import re
from backend.app.config import credential


def redact(value, secret=None):
    if isinstance(value,dict):
        return {k:('[REDACTED]' if any(s in k.lower() for s in ('api_key','authorization','password','secret')) else redact(v,secret)) for k,v in value.items()}
    if isinstance(value,list): return [redact(v,secret) for v in value]
    if isinstance(value,str):
        if secret: value=value.replace(secret,'[REDACTED]')
        value=re.sub(r'(?i)\b(Bearer\s+)[\w.\-]{15,}',r'\1[REDACTED]',value)
        return re.sub(r'\b(?:sk-|wandb_v1_)[A-Za-z0-9_\-]{15,}','[REDACTED]',value)
    return value


class WeaveIntegration:
    def __init__(self,settings):
        self.settings=settings
        self.client=None
        self.status='unavailable'

    async def initialize(self):
        key=credential(self.settings)
        if not key:
            self.status='authentication required'
            return False
        if self.client: return True
        def init():
            import weave
            os.environ['WANDB_API_KEY']=key
            return weave.init(self.settings.project_id,settings={'print_call_link':False},postprocess_inputs=lambda v:redact(v,key),postprocess_output=lambda v:redact(v,key))
        try:
            self.client=await asyncio.wait_for(asyncio.to_thread(init),25)
            self.status='initialized; awaiting trace verification'
            return True
        except Exception:
            self.status='unavailable: project authentication or network failed'
            return False

    def begin(self,run_id,mode):
        return Trajectory(self,run_id,mode)


class Trajectory:
    def __init__(self,integration,run_id,mode):
        self.integration=integration
        self.client=integration.client if mode=='live' else None
        self.root=None
        self.open={}
        self.failed=False
        if self.client:
            try: self.root=self.client.create_call('optara.execute_task',{'task_id':run_id},attributes={'product':'Optara','mode':mode},use_stack=False)
            except Exception: self.failed=True

    def event(self,event):
        if not self.root or self.failed: return
        try:
            stage=event['stage']
            if event['status']=='active':
                if stage in self.open: self.client.finish_call(self.open.pop(stage),output={'status':'continued'})
                self.open[stage]=self.client.create_call(f'optara.{stage}',{'task_id':event['run_id']},parent=self.root,use_stack=False)
            else:
                child=self.open.pop(stage,None) or self.client.create_call(f'optara.{stage}',{'task_id':event['run_id']},parent=self.root,use_stack=False)
                self.client.finish_call(child,output=redact(event,credential(self.integration.settings)))
        except Exception: self.failed=True

    async def finish(self,result):
        if not self.root: return None,None,'unavailable' if result.task.mode=='live' else 'simulation · no remote trace'
        try:
            for child in self.open.values(): self.client.finish_call(child,output={'status':'interrupted'})
            self.open.clear()
            self.client.finish_call(self.root,output=redact(result.model_dump(mode='json'),credential(self.integration.settings)))
            await asyncio.wait_for(asyncio.to_thread(self.client.flush),20)
            remote=await asyncio.wait_for(asyncio.to_thread(self.client.get_call,self.root.id),15)
            if remote.id==self.root.id:
                self.integration.status='connected'
                return self.root.id,self.root.ui_url,'recorded' if not self.failed else 'recorded · partial stage logging'
        except Exception: pass
        return self.root.id,None,'upload not verified'
