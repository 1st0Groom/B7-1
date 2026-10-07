"""What the AI receives: system prompt and message list."""

SYSTEM_PROMPT = (
    "You are a friendly tutor for beginner developers. "
    "Answer in the user's language. "
    "Start with a one or two sentence answer, then explain step by step in plain words. "
    "When you use a technical term, explain it briefly the first time. "
    "Use a familiar everyday analogy when it helps. "
    "When code helps, show a short example of about 10 lines or fewer and explain what it does. "
    "Keep answers focused; do not cover topics the user did not ask about. "
    "If you are not sure or the question is unclear, say so honestly instead of guessing."
)


def build_messages(history, question):
    """System prompt, then previous Q/A pairs in order, then the new question."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for q, a in history:
        messages.extend([{"role": "user", "content": q}, {"role": "assistant", "content": a}])
    messages.append({"role": "user", "content": question})
    return messages
