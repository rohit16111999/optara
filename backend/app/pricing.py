import json
from .config import ROOT


def prices():
    return json.loads((ROOT / 'data/pricing.json').read_text())


def token_cost(model, input_tokens, output_tokens):
    if model.input_price_per_million is None or model.output_price_per_million is None:
        return None
    return (input_tokens * model.input_price_per_million + output_tokens * model.output_price_per_million) / 1_000_000


def upper_cost(model, messages, max_tokens):
    # UTF-8 byte count + generous per-message overhead bounds byte-level tokenizers.
    # Output budget includes reasoning where the provider supports reasoning.
    inputs = sum(len(m['content'].encode('utf-8')) + 64 for m in messages) + 256
    return token_cost(model, inputs, max_tokens)
