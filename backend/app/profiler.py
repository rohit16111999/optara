import re
from .evaluator import reference_spec
from .schemas import TaskProfile, TaskRequest


def profile_task(task: TaskRequest) -> TaskProfile:
    text = task.prompt.lower()
    families = [
        ('coding', r'\b(python|function|implement|algorithm|code|javascript)\b'),
        ('extraction', r'\b(extract|fields|invoice)\b'),
        ('structured', r'\b(json|schema|transform|csv)\b'),
        ('math', r'\b(calculate|compute|solve|how many|arithmetic)\b|\d\s*[+*/×-]\s*\d'),
        ('classification', r'\b(classify|sentiment|label)\b'),
        ('summarization', r'\b(summarize|summary|summarise)\b'),
        ('writing', r'\b(write|poem|story|draft)\b'),
    ]
    family = next((name for name, pattern in families if re.search(pattern, text)), 'reasoning')
    if task.task_family in {f[0] for f in families} | {'reasoning'}:
        family = task.task_family
    fresh = bool(re.search(r'\b(current|latest|today|now|weather|stock price|news|my account|my calendar|tomorrow)\b', text))
    structured = family in {'structured', 'extraction'} or 'json' in text
    difficulty = min(.95, .25 + len(text)/6000 + .15 * sum(w in text for w in ('prove', 'complex', 'optimize', 'o(n)', 'concurrent')))
    deterministic = bool(reference_spec(task))
    return TaskProfile(task_family=family, difficulty=round(difficulty, 2), uncertainty=.15 if deterministic else .45,
        required_skills=[family] + (['structured_output'] if structured else []), structured_output_required=structured,
        evaluation_type='deterministic' if deterministic else 'rubric', freshness_sensitive=fresh, cacheable=not fresh,
        explanation=f'{family.title()} task identified from task constraints. '+('Reference checks are available.' if deterministic else 'Quality needs a rubric estimate.')+(' Freshness-sensitive: cache disabled.' if fresh else ' Stable task: eligible for validated caching.'))
