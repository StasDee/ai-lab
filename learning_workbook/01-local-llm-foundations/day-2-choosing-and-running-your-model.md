# Module 1, Day 2: Choosing Your Model and Running It Locally
### ~1-1.5 hrs

## Objective

By the end of today you have a real model loaded and serving requests on
your machine, through both of the two runtimes you'll use throughout this
workbook.

---

## Theory

### Your hardware sets the range, not the ceiling

No GPU, 64GB RAM means CPU-only inference. That's a real constraint, but
it's a workable one: the realistic range for *interactive* use (i.e., you're
sitting there waiting for a response, not running an overnight batch job) is
**dense models in the 3B-14B parameter range at Q4**, typically landing
somewhere in the range of high single digits to mid-teens tokens/sec on a
modern CPU: the exact number depends heavily on your specific CPU, so
tomorrow's benchmark (Day 4 of this module) will give you your real number
rather than a generic estimate.

### Model choices for this workbook

- **Workhorse: Qwen2.5-Coder-7B-Instruct (Q4_K_M).** Strong at coding and
  tool-calling relative to its size, and comfortably inside your RAM budget
  per yesterday's calculation. This is the model most of this workbook
  assumes by default.
- **Fast/simple tasks: a 3-4B model** (e.g. Phi-4-mini or Llama-3.2-3B).
  Lower latency, less reasoning depth: useful when you don't need the 7B's
  full capability and want a snappier response, or when you want a second
  data point for tomorrow's benchmark.
- **Forward-look to Round 2:** mixture-of-experts models (e.g.
  Qwen3-Coder-30B-A3B) have a large *total* parameter count but activate
  only a small fraction per token, which changes the memory/speed math in a
  way dense models don't. You don't need this yet, just file it away, you'll
  come back to it once you outgrow dense 7B models in Round 2.

### The two runtimes, and when to reach for each

- **LM Studio**: GUI application with a built-in model browser, exposes an
  OpenAI-compatible local server, and (relevant later) has a built-in MCP
  host you'll use in Module 3. Best for exploration, comparing models, and
  quick manual testing.
- **Ollama**: CLI-first and scriptable. This is the one you'll more often
  see referenced in job postings, CI pipelines, and infra-as-code setups,
  because it's trivial to automate.

You'll set up both today, not because you need both running simultaneously
day-to-day, but because you'll want the comparison firsthand, and because
job-relevant familiarity with both is part of the point of this workbook.

---

## Practice

### LM Studio

1. Download from **lmstudio.ai** and install.
2. In the app's model browser, search for a **GGUF build of
   Qwen2.5-Coder-7B-Instruct**, and download the **Q4_K_M** variant
   specifically (multiple quant levels are usually offered, pick the one
   you planned around yesterday).
3. Load the model in the Chat tab and confirm it responds to a basic prompt.
4. Enable **Local Server** (default port `1234`): this exposes the
   OpenAI-compatible endpoint you'll call from Python tomorrow.
5. Verify the server is live:
   ```bash
   curl http://localhost:1234/v1/models
   ```
   You should get back JSON listing your loaded model.

### Ollama

```bash
ollama pull qwen2.5-coder:7b
ollama run qwen2.5-coder:7b   # quick interactive terminal test, Ctrl+D to exit
```

Ollama exposes its API by default at `http://localhost:11434`. Verify:

```bash
curl http://localhost:11434/api/tags
```

### If the model won't load

If LM Studio or Ollama complains about memory rather than loading the model,
your options are, in order of preference:
1. Drop to a smaller model (3-4B) at the same quant level
2. Drop to a more aggressive quant of the same model (accepting the
   tool-calling risk from yesterday, and reconsidering before Module 2)
3. Close other memory-heavy applications and retry

---

## Assignment

Produce `docs/setup-notes.md` containing:

1. Exact versions of LM Studio and Ollama you installed
2. The exact model + quant you loaded in each
3. One real request/response pair from **each** runtime's API (the `curl`
   output from the verification steps above is enough)
4. A one-line comparison: which felt easier to set up, and which do you
   expect to reach for day-to-day going forward

---

## Self-Check

- If you had a GPU tomorrow, what would change about your model choice, and what wouldn't?
- Why do both LM Studio and Ollama expose an OpenAI-compatible API, even though neither is OpenAI? What does that buy you as the developer calling them?
- What's the actual measured tokens/sec you saw in LM Studio's UI during your test prompt, and how does that compare to your Day 1 expectation?

**Next:** Day 3, calling your local model from Python, the same way your Module 2 agent loop will.
