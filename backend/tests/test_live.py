import os
import pytest


@pytest.mark.live
@pytest.mark.skipif(os.getenv('OPTARA_LIVE_TEST')!='1',reason='Paid integration check requires OPTARA_LIVE_TEST=1')
async def test_tiny_real_wandb_trace():
    from scripts.verify_wandb import verify
    result=await verify()
    assert result['inference'] and result['weave'] and result['tokens']>0
