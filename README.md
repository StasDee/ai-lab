# [Project Name]: e.g. "Sentinel: Local AI Test-Failure Triage Agent"

> [One-line pitch: what it is, in a sentence a non-QA person would understand]
> Example: "An offline AI agent that reads failing Playwright/pytest runs, diagnoses the root cause, and proposes a fix, no cloud API, no test data leaving your machine."

[Demo GIF or short video: link/embed here]

---

## The Problem

<!-- 2-3 sentences on real pain. Be specific and concrete, not generic.
Example angle: "Triaging a flaky Playwright suite eats N hours/week. Cloud AI
tools that could help mean sending test logs, screenshots, and sometimes
production data to a third party, a non-starter for [reason]." -->

[FILL IN]

## Demo

<!-- Highest-value real estate in this file. Put it early. 30-60 seconds. -->

![demo](docs/assets/demo.gif)

## What It Does

- [ ] Diagnoses failing test runs (pytest / Playwright) by reading logs and stack traces
- [ ] Proposes a root-cause explanation and a concrete fix
- [ ] Can generate a new test case from a requirements doc / spec
- [ ] Runs entirely offline: no API calls, no data leaves your machine
- [ ] <!-- add/remove to match what you actually built -->

## Key Engineering Decisions

<!-- This section is what actually signals seniority, not the demo.
Be specific about the trade-off, not just the choice. -->

| Decision | Choice | Why |
|---|---|---|
| Model | Qwen2.5-Coder-7B-Instruct (Q4_K_M), local | [FILL IN: e.g. privacy requirement + no GPU meant X tokens/sec was the ceiling; traded Y for Z] |
| Tool-calling | MCP over hand-rolled function calling | [FILL IN: why: reuse, standardization, ecosystem (Playwright MCP)] |
| Agent pattern | Hand-rolled ReAct loop (not a framework) | [FILL IN: why understanding every step mattered more than framework convenience, at this scale] |
| Quantization | Q4_K_M | [FILL IN: the quality/speed/memory trade-off you actually measured] |

## Architecture at a Glance

<!-- One small diagram + one paragraph. Full depth lives in docs/architecture.md -->

```
[failing test run] -> [MCP server: log/report tools] -> [local LLM agent loop] -> [diagnosis + fix proposal] -> [PR comment / CI annotation]
```

[FILL IN: one paragraph summary of how it flows end to end]

See [`docs/architecture.md`](docs/architecture.md) for the full breakdown.

## Tech Stack

- Python 3.x
- [LM Studio](https://lmstudio.ai) / [Ollama](https://ollama.com): local model runtime
- [Model Context Protocol](https://modelcontextprotocol.io): official Python SDK
- [Playwright](https://playwright.dev) / pytest
- [FILL IN: anything else: Docker, GitHub Actions, ChromaDB, Langfuse, etc.]

## Quickstart

```bash
# clone
git clone [repo-url]
cd [repo-name]

# install
pip install -r requirements.txt

# start your local model server (LM Studio or Ollama)
# [FILL IN exact command/instructions]

# run the agent
python agent.py --target [failing-test-report-path]
```

## Limitations & What's Next

<!-- Genuinely valuable. Knowing what's NOT solved reads as more senior than
pretending it's finished. -->

- [FILL IN: e.g. tool-calling reliability drops on multi-step chains beyond N steps]
- [FILL IN: e.g. no sandboxing yet on the MCP server: planned via Docker]
- [FILL IN: e.g. single-agent only; Round 2 explores multi-agent via LangGraph]

## License

[FILL IN: MIT is a common default for portfolio projects]
