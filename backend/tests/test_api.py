from fastapi.testclient import TestClient
from backend.app.main import create_app


def test_health_and_truthful_integrations(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get('/api/health').status_code==200
        status=client.get('/api/status/integrations').json()
        assert not status['aria']['available'] and not status['typesafe']['available']
        assert status['marimo']['available']


def test_api_validation_origin_and_upper_cap(settings):
    with TestClient(create_app(settings)) as client:
        assert client.post('/api/runs',json={'prompt':' '}).status_code==422
        assert client.post('/api/runs',json={'prompt':'x','max_budget_usd':.1}).status_code==422
        assert client.post('/api/runs',json={'prompt':'x'},headers={'Origin':'https://evil.example'}).status_code==403
        assert client.get('/api/runs/missing').status_code==404


def test_configured_production_origin(settings):
    settings.allowed_origins='https://optara.example'
    with TestClient(create_app(settings)) as client:
        response=client.post('/api/runs',json={'prompt':'Reply with exactly: PUBLIC_OK','mode':'simulation'},headers={'Origin':'https://optara.example'})
        assert response.status_code==202
        assert response.headers['access-control-allow-origin']=='https://optara.example'
        assert client.post('/api/runs',json={'prompt':'x'},headers={'Origin':'https://untrusted.example'}).status_code==403


def test_sse_replay_and_final_result(settings):
    with TestClient(create_app(settings)) as client:
        response=client.post('/api/runs',json={'prompt':'Reply with exactly: OK','mode':'simulation'})
        assert response.status_code==202
        id=response.json()['run_id']
        stream=client.get(f'/api/runs/{id}/events')
        assert 'text/event-stream' in stream.headers['content-type']
        assert '"stage": "done"' in stream.text
        result=client.get(f'/api/runs/{id}').json()
        assert result['output']=='OK' and result['quality']==1
        replay=client.get(f'/api/runs/{id}/events',headers={'Last-Event-ID':'2'})
        assert 'id: 1\n' not in replay.text and 'id: 2\n' not in replay.text


def test_restart_marks_interrupted(settings):
    from backend.app.persistence import Store
    from backend.app.schemas import TaskRequest,RunResult
    store=Store(settings.optara_db_path)
    task=TaskRequest(prompt='test')
    store.put('runs',task.task_id,RunResult(run_id=task.task_id,task=task,status='running'))
    with TestClient(create_app(settings)) as client:
        result=client.get(f'/api/runs/{task.task_id}').json()
        assert result['status']=='interrupted'
