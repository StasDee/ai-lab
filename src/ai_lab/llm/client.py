"""Local model access, shared by every agent in this project.

One place that knows how to reach the model, so swapping LM Studio for
Ollama (or, later, a cloud endpoint for a CI run) is a change to this file
and nowhere else. Day 3's lesson makes the point that only ``base_url``
differs between a local runtime and a hosted API: this module is where
that fact gets to stay true.

Both functions are deliberately thin: they return values rather than
printing, so callers (the benchmark script, the agent loop, tests) can do
their own thing with the result.
"""

import os
import time

from openai import OpenAI

DEFAULT_BASE_URL = os.environ.get("AI_LAB_BASE_URL", "http://localhost:1234/v1")
DEFAULT_MODEL = os.environ.get("AI_LAB_MODEL", "qwen2.5-coder-7b-instruct")

client = OpenAI(
    base_url=DEFAULT_BASE_URL,  # :1234/v1 LM Studio, :11434/v1 Ollama
    api_key="not-needed",       # local servers ignore this, but the client requires it
)


def run_non_streaming(prompt: str, model: str = DEFAULT_MODEL, temperature: float = 0.2):
    """Send one prompt and wait for the whole reply.

    Returns:
        (elapsed_seconds, text)
    """
    start = time.time()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    elapsed = time.time() - start
    return elapsed, response.choices[0].message.content


def run_streaming(prompt: str, model: str = DEFAULT_MODEL, temperature: float = 0.2):
    """Send one prompt and consume the reply token by token.

    Captures time-to-first-token on the first non-empty delta, which is the
    only way to measure TTFT at all (Day 4, section 4).

    Returns:
        (ttft_seconds, total_seconds, text)
    """
    start = time.time()
    ttft = None
    chunks = []

    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            if ttft is None:
                ttft = time.time() - start
            chunks.append(delta)

    total = time.time() - start
    return ttft, total, "".join(chunks)
