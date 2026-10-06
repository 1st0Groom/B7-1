"""What the AI receives: system prompt and message list."""

SYSTEM_PROMPT = (
    "You are a helpful learning assistant. Explain concepts clearly, use examples when useful, "
    "and answer in the user's language. Be honest when uncertain."
)


def build_messages(history, question):
    """System prompt, then previous Q/A pairs in order, then the new question."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for q, a in history:
        messages.extend([{"role": "user", "content": q}, {"role": "assistant", "content": a}])
    messages.append({"role": "user", "content": question})
    return messages
