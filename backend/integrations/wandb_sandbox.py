import os


def status():
    configured=bool(os.getenv('CWSANDBOX_API_KEY'))
    return {'available':False,'detail':('Credential detected; runner access unverified.' if configured else 'No CoreWeave Sandbox credential/runner. Local bounded AST interpreter evaluates supported Python exercises.')}
