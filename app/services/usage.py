from flask import current_app

def calculate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    """Compute USD cost from token counts using the app's configured rates."""
    prompt_rate = current_app.config["PRICE_PER_1M_PROMPT_TOKENS"]
    completion_rate = current_app.config["PRICE_PER_1M_COMPLETION_TOKENS"]
    return (prompt_tokens * prompt_rate + completion_tokens * completion_rate) / 1_000_000
