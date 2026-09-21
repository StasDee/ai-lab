# Module 1, Day 3: Calling Your Local Model From Python
### ~1-1.5 hrs

## Objective

By the end of today you have working Python code that talks to your local
model: using the exact pattern your Module 2 agent loop will reuse, so this
stops being a new thing to learn by the time you need it there.

---

## Theory

### Why "OpenAI-compatible" became the default interface

Both LM Studio and Ollama expose an API shaped like OpenAI's
chat-completions endpoint. This isn't coincidence: it happened because the
`openai` Python client became the de facto way developers already knew how
to call an LLM, so local runtimes adopted the same request/response shape to
lower the switching cost. The practical benefit for you: **the only thing
that changes between calling OpenAI's cloud API and your local server is the
`base_url`.** Everything else (message format, roles, parameters) stays
the same.

### The shape of a request

A chat completion request is a list of messages, each with a `role`
(`system`, `user`, or `assistant`) and `content`. The model doesn't see your
Python code: it sees this message list rendered through its chat template
into a single prompt string, and predicts what comes next.

Two parameters matter most for what you're building:

- **`temperature`**: controls randomness. Lower (e.g. `0.2`) makes output
  more deterministic and repeatable; higher (e.g. `0.8`+) makes it more
  varied/creative. For anything that has to produce structured, parseable
  output (like a tool call) you want low temperature. Save higher values
  for open-ended creative tasks, which isn't what this workbook is about.
- **Streaming vs. non-streaming**: streaming returns tokens as they're
  generated (better perceived responsiveness for a chat UI); non-streaming
  waits for the full response before returning it. Agent loops that need to
  parse a complete tool call before acting typically use non-streaming, so
  that's what you'll use in Module 2, but it's worth knowing streaming
  exists, since you'll want it later for anything user-facing.

---

## Practice

### The base pattern

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",  # LM Studio; use :11434/v1 for Ollama
    api_key="not-needed",                 # local servers typically ignore this
)

response = client.chat.completions.create(
    model="qwen2.5-coder-7b-instruct",
    messages=[{"role": "user", "content": "Explain what GGUF is in two sentences."}],
    temperature=0.2,
)

print(response.choices[0].message.content)
```

Run this against your LM Studio server first. Then:

1. **Inspect the full response object**, not just `.content`: print
   `response.usage` to see prompt/completion token counts, and
   `response.model` to confirm which model actually answered.
2. **Change `temperature` to 0.9`** and run the same prompt 3 times: notice
   how much more the wording varies compared to `0.2`.
3. **Point the same code at Ollama** by changing only `base_url` to
   `http://localhost:11434/v1` (and `model` to match Ollama's naming, e.g.
   `qwen2.5-coder:7b`): confirm the exact same code works unmodified
   otherwise.

---

## Assignment

Write `src/local_client.py`: a small reusable helper, not a one-off script.

Requirements (your acceptance criteria):

- A function `chat(prompt: str, model: str, base_url: str, temperature: float = 0.2) -> str`
  that wraps the boilerplate above and returns just the response text
- Runs successfully against **both** LM Studio and Ollama by only changing
  the `base_url`/`model` arguments: no code changes between the two calls
- A `if __name__ == "__main__":` block at the bottom that calls it against
  both runtimes with the same prompt and prints both results, so running the
  file directly demonstrates it works

This file isn't throwaway: Module 2's agent loop imports this same pattern,
so getting the interface right now saves you a rewrite later.

---

## Self-Check

- What's the practical difference between `temperature=0.2` and `temperature=0.8` for a model that must emit exact tool-call syntax?
- Why is having a shared interface (OpenAI-compatible) valuable, given you'll likely switch models or runtimes multiple times in this workbook?
- Looking at `response.usage`, how many tokens did your test prompt actually cost, and does that match your intuition from reading it?

**Next:** Day 4, benchmarking your model properly, and closing out Module 1.
