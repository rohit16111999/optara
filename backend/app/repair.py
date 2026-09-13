from .spend_guard import GuardError


def repair_messages(task,output,evaluation):
    return [{'role':'system','content':'Repair the specific failed constraints below. Preserve correct parts. Return the complete corrected answer only. For code, retain the required function name. Do not change or weaken tests.'},
        {'role':'user','content':f'TASK:\n{task.prompt}\n\nPREVIOUS ANSWER:\n{output}\n\nFAILED CHECKS:\n{evaluation.explanation}'}]


def can_repair(guard,count,recipe,settings):
    if count>=min(recipe.repair_limit,settings.max_repairs_per_request): return False,'Repair limit reached'
    if guard.remaining_seconds<.25: return False,'Insufficient deadline remaining'
    if guard.calls>=settings.max_model_calls_per_request: return False,'Call limit reached'
    return True,'Targeted constraint repair'
