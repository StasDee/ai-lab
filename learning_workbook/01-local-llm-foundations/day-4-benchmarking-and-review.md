# Module 1, Day 4: Benchmarking Properly, and Module Review
### ~1-1.5 hrs

## Objective

By the end of today you have real, reusable performance numbers for your
model choice (not a vague impression of "feels fast enough") and you've
tied together everything from this module into one working setup.

---

## Theory

### Why tokens/sec alone isn't enough

Tokens/sec tells you throughput once generation is underway, but it misses
two things that matter just as much for an agent:

- **Time-to-first-token (TTFT)**: how long before *anything* appears. This
  is what makes an agent loop feel responsive or sluggish, especially across
  a multi-step session where the model is called repeatedly. A model with
  great tokens/sec but slow TTFT can still feel bad to use interactively.
- **Tool-call format validity under load**: does the model still emit
  well-formed tool calls on, say, the 20th turn of a long agent session, or
  does quality drift as context grows? This connects directly back to Day
  1's point about quantization and structured output: it's worth actually
  observing, not just taking on faith.

### Why you run multiple prompts, not one

A single prompt's timing is noisy: background OS activity, thermal
throttling, and prompt-length variance all shift the number run-to-run.
Running the *same* set of realistic-length prompts multiple times and
averaging gives you a number you can actually trust and compare against
later (e.g., once you try a bigger model in Round 2).

---

## Practice

Build a small benchmark script. The core idea:

```python
import time
from local_client import chat  # from Day 3

PROMPTS = [
    "Explain the difference between a list and a tuple in Python.",
    "Write a function that reverses a string without using slicing.",
    "What does the SOLID acronym stand for in software design?",
    "Summarize what a race condition is, in three sentences.",
    "Convert this pseudocode to Python: for i from 1 to 10, print i squared.",
]

def benchmark(model: str, base_url: str, prompts=PROMPTS, runs: int = 3):
    results = []
    for prompt in prompts:
        for _ in range(runs):
            start = time.time()
            output = chat(prompt, model=model, base_url=base_url)
            elapsed = time.time() - start
            approx_tokens = len(output.split())  # rough proxy, good enough here
            results.append({
                "prompt": prompt[:40],
                "elapsed_sec": round(elapsed, 2),
                "approx_tokens": approx_tokens,
                "approx_tokens_per_sec": round(approx_tokens / elapsed, 2) if elapsed > 0 else None,
            })
    return results
```

This is a starting point, not a finished tool: notably, it doesn't isolate
true time-to-first-token (that requires streaming and timing the first
chunk specifically, which is worth attempting as a stretch goal, but a
non-streaming elapsed-time proxy is good enough to start comparing models).

Run this against both of your downloaded models (7B and 3-4B) and save the
raw output.

---

## Assignment

Produce `docs/benchmarks.md` containing:

1. Your raw results table for both models (prompt, elapsed time, approx
   tokens/sec): at least 3 runs per prompt, averaged
2. A short note on variance you observed between runs
3. A one-paragraph recommendation: which model you're carrying forward into
   Module 2, and why: referencing your Day 1 memory budget, Day 2 hands-on
   feel, and today's numbers together

This file is referenced directly from `docs/architecture.md`: it's real
content for your capstone project's documentation, not disposable practice.

---

## Module 1 Review

Walk back through what connects across the four days:

- **Day 1** gave you the memory-budgeting mental model and the
  quantization/tool-calling relationship that explains *why* Q4_K_M is this
  workbook's floor.
- **Day 2** turned that into a real, running model in two different
  runtimes.
- **Day 3** gave you a reusable Python interface to call it: the same
  interface Module 2's agent loop will import directly.
- **Day 4** turned "it works" into "I have numbers proving how well it
  works," which becomes real content in your capstone documentation.

## Self-Check

- Why does aggressive quantization (Q2/Q3) hurt tool-calling more than plain chat? *(revisit your Day 1 answer; has anything changed now that you've seen it running?)*
- What's the practical difference between tokens/sec and time-to-first-token, and why would an agent loop care about both?
- Which model are you carrying into Module 2, and can you defend that choice using data from all four days, not just one?

## External Links

- LM Studio docs: https://lmstudio.ai/docs
- Ollama: https://ollama.com
- llama.cpp (GGUF format, quantization internals): https://github.com/ggml-org/llama.cpp
- OpenAI Python client (used to call local servers): https://github.com/openai/openai-python

---

**Next:** Module 2, Python Agents From Scratch. You have a model that talks and numbers proving how well it talks; now you make it act.
