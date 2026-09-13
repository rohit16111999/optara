from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskRequest(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    prompt: str = Field(min_length=1, max_length=16000)
    quality_target: float = Field(default=.9, ge=0, le=1)
    max_budget_usd: float = Field(default=.02, gt=0, le=1)
    max_latency_seconds: float = Field(default=45, gt=0, le=180)
    priority: Literal['standard', 'high', 'background'] = 'standard'
    task_family: str | None = None
    timestamp: str = Field(default_factory=now)
    mode: Literal['live', 'simulation'] = 'live'
    bypass_cache: bool = False
    # Reference tests are explicitly supplied by the caller, never model generated.
    evaluation_spec: dict[str, Any] = Field(default_factory=dict)

    @field_validator('prompt')
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError('Enter a task to optimize.')
        return value.strip()

    @field_validator('evaluation_spec')
    @classmethod
    def bounded_spec(cls,value):
        import json
        encoded=json.dumps(value)
        if len(encoded)>24000: raise ValueError('Reference specification is too large')
        def visit(x):
            if isinstance(x,dict):
                for k,v in x.items():
                    if k=='$ref' and (not isinstance(v,str) or not v.startswith('#')): raise ValueError('Only local schema references are supported')
                    visit(v)
            elif isinstance(x,list):
                for v in x: visit(v)
        visit(value)
        return value


class TaskProfile(BaseModel):
    task_family: str
    difficulty: float
    uncertainty: float
    required_skills: list[str]
    structured_output_required: bool
    evaluation_type: str
    freshness_sensitive: bool
    cacheable: bool
    explanation: str


class ModelSpec(BaseModel):
    model_id: str
    provider: str = 'W&B Serverless Inference'
    enabled: bool = True
    input_price_per_million: float | None = None
    output_price_per_million: float | None = None
    capabilities: list[str] = Field(default_factory=lambda: ['text'])
    context_window: int | None = None
    reasoning_support: bool = False
    metadata: dict = Field(default_factory=dict)
    last_verified: str | None = None


class Recipe(BaseModel):
    recipe_id: str
    model_id: str
    name: str
    version: int = 1
    reasoning: str | None = None
    max_output_tokens: int = Field(ge=32, le=4096)
    verifier_enabled: bool = False
    verifier_model: str | None = None
    agents: int = Field(default=1, ge=1, le=2)
    parallelism: Literal['sequential', 'parallel'] = 'sequential'
    repair_limit: int = Field(default=1, ge=0, le=2)
    evaluator_strategy: str = 'deterministic_or_rubric'
    metadata: dict = Field(default_factory=dict)


class ExpectedMetrics(BaseModel):
    expected_quality: float = .5
    expected_cost: float | None = None
    expected_latency: float = 15
    observations: int = 0
    uncertainty: float = .5
    last_updated: str | None = None
    source: str = 'Uncalibrated prior; not measured performance'


class Candidate(BaseModel):
    recipe: Recipe
    metrics: ExpectedMetrics
    selected: bool = False
    feasible: bool = False
    rejection_reason: str | None = None
    rank: int = 0


class ExecutionResult(BaseModel):
    output: str = ''
    model_id: str
    recipe_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float | None = None
    latency_seconds: float = 0
    started_at: str = Field(default_factory=now)
    ended_at: str | None = None
    provider_metadata: dict = Field(default_factory=dict)
    error: str | None = None


class EvaluationResult(BaseModel):
    score: float = Field(ge=0, le=1)
    passed: bool
    evaluation_type: str
    explanation: str
    confidence: float = Field(ge=0, le=1)
    deterministic: bool
    evaluator_metadata: dict = Field(default_factory=dict)


class RunResult(BaseModel):
    run_id: str
    task: TaskRequest
    status: str = 'queued'
    profile: TaskProfile | None = None
    candidate_recipes: list[Candidate] = Field(default_factory=list)
    rejected_candidates: list[Candidate] = Field(default_factory=list)
    selected_recipe: Recipe | None = None
    scheduler_reason: str = ''
    executions: list[ExecutionResult] = Field(default_factory=list)
    evaluations: list[EvaluationResult] = Field(default_factory=list)
    final_evaluation: EvaluationResult | None = None
    repair_steps: list[dict] = Field(default_factory=list)
    shadow_result: dict | None = None
    output: str = ''
    total_cost: float | None = None
    total_latency: float = 0
    quality: float | None = None
    sla_hit: bool = False
    sla_failures: list[str] = Field(default_factory=list)
    trace_url: str | None = None
    trace_id: str | None = None
    trace_status: str = 'unavailable'
    cache_hit: bool = False
    error: str | None = None
    policy_version: int | None = None


class Policy(BaseModel):
    policy_id: str
    version: int
    task_family: str
    recipe_preferences: list[str]
    evidence_count: int = 0
    confidence: float = 0
    creation_reason: str
    status: Literal['candidate', 'shadow', 'production', 'rejected'] = 'candidate'
    created_at: str = Field(default_factory=now)
    promoted_at: str | None = None
    mode: str = 'live'
    comparison: dict = Field(default_factory=dict)
