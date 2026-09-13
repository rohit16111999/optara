from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', env_ignore_empty=True, extra='ignore')
    wandb_api_key: SecretStr | None = None
    wandb_entity: str = 'models-student1155'
    wandb_project: str = 'optara'
    wandb_mcp_url: str = 'https://mcp.withwandb.com/mcp'
    allowed_origins: str = 'http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:8000,http://localhost:8000'
    max_cost_per_request: float = Field(default=.05, gt=0, le=1)
    max_total_dev_spend: float = Field(default=2, gt=0, le=20)
    max_calibration_spend: float = Field(default=.25, gt=0, le=5)
    max_benchmark_spend: float = Field(default=.25, gt=0, le=5)
    max_shadow_spend: float = Field(default=.10, gt=0, le=1)
    max_model_calls_per_request: int = Field(default=5, ge=1, le=10)
    max_repairs_per_request: int = Field(default=1, ge=0, le=2)
    shadow_exploration_rate: float = Field(default=.08, ge=0, le=.25)
    dry_run_mode: bool = False
    top_k: int = Field(default=3, ge=1, le=5)
    policy_min_evidence: int = Field(default=5, ge=3)
    policy_quality_tolerance: float = Field(default=.02, ge=0, le=.1)
    policy_confidence_z: float = Field(default=1.96, ge=1.64, le=3)
    policy_min_latency_improvement: float = Field(default=.01, ge=0)
    optara_db_path: Path = ROOT / 'data' / 'optara.db'

    @property
    def project_id(self):
        return f'{self.wandb_entity}/{self.wandb_project}'


def credential(settings: Settings) -> str | None:
    """Read only the standard W&B credential locations. Never return it via API."""
    import os
    import netrc
    key = os.getenv('WANDB_API_KEY') or (settings.wandb_api_key.get_secret_value() if settings.wandb_api_key else None)
    if key:
        return key
    for name in ('.netrc', '_netrc'):
        try:
            auth = netrc.netrc(str(Path.home() / name)).authenticators('api.wandb.ai')
            if auth:
                return auth[2]
        except (OSError, netrc.NetrcParseError):
            pass
    return None
