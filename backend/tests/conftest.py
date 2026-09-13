import pytest
from backend.app.config import Settings
from backend.app.persistence import Store
from backend.app.inference import InferenceEngine
from backend.app.controller import Controller
from backend.integrations.weave_integration import WeaveIntegration
from backend.integrations.wandb_inference import WandbInference


@pytest.fixture
def settings(tmp_path): return Settings(optara_db_path=tmp_path/'test.db',shadow_exploration_rate=0)


@pytest.fixture
def store(settings): return Store(settings.optara_db_path)


@pytest.fixture
def controller(store,settings): return Controller(store,settings,InferenceEngine(WandbInference(settings)),WeaveIntegration(settings))
