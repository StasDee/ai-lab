# Round 1: CV & Interview Ready
### Local LLMs → Python Agents → MCP → Test Automation

**Goal:** A working, defensible local-agent project plus the ability to talk fluently about trade-offs in an interview.
**Hardware:** i5, 64GB RAM, no GPU: CPU-only inference throughout.
**Adjusted for experience:** With vast automation experience already in hand, Weeks 1-2 below likely compress to days, not weeks. Reinvest the saved time into the trade-off questions at the end and into making the Week 4 capstone read as senior work. Realistic total: 3-4 weeks.

---

## Week 1: Local LLM Foundations
- [ ] Install LM Studio (GUI, built-in MCP host) and Ollama (CLI)
- [ ] Learn GGUF/quantization basics: what Q4 vs Q5 vs Q8 trades off
- [ ] Set your workhorse model: Qwen2.5-Coder-7B-Instruct (Q4_K_M)
- [ ] Keep a 3-4B model on hand for low-latency tasks (Phi-4-mini or Llama-3.2-3B)
- [ ] **Deliverable:** a tokens/sec benchmark write-up on your own machine, a concrete, portfolio-ready artifact

## Week 2: Python Agents From Scratch
- [ ] Hand-build a minimal ReAct loop yourself: prompt → parse tool call → execute → feed result back
- [ ] No framework: 2-3 toy tools (read a file, run a shell command, hit a REST endpoint)
- [ ] Then wire the same loop through smolagents against your local model, via the OpenAI-compatible endpoint LM Studio/Ollama expose
- [ ] **Deliverable:** a small "mini-agent" repo you can explain line by line

## Week 3: MCP + Real Test Tooling
- [ ] Learn MCP's client/host/server model and transports (stdio vs HTTP/SSE)
- [ ] Install Playwright MCP (Microsoft's official server) and connect it via LM Studio's built-in MCP host
- [ ] Write your own minimal MCP server using the official Python `mcp` SDK, exposing 2-3 test-automation tools: e.g. `run_pytest_suite`, `get_last_failure_log`
- [ ] Drive your custom server with your local model end-to-end

## Week 4: Capstone + CV Polish (senior-level version)
- [ ] Flagship project: an agent that reads a failing pytest/Playwright run via your MCP server, diagnoses it, and proposes a fix or new test
- [ ] Add observability: log/trace every tool call and model decision
- [ ] Add a sandboxing story for the MCP server: Docker or restricted filesystem/network access, even if not fully implemented
- [ ] Add a failure-mode plan: what happens when the agent's diagnosis or fix is wrong
- [ ] Tie into CI: a real or mocked GitHub Actions step that triggers the agent on a failing run
- [ ] GitHub repo: README, architecture diagram, short demo clip

---

## Interview Cheat Sheet: Be Ready to Defend
- Why MCP over hand-rolled function calling?
- Why a local model for this task vs. an API model for that one?
- What does quantization actually cost you: quality vs. speed vs. memory?
- Where does tool-calling reliability break down as chains get longer?
- How would you secure/sandbox an MCP server with filesystem or shell access?
- What's your plan when the agent's diagnosis or fix is simply wrong?

## CV Bullet
"Built a local, offline LLM test-automation agent (Python, LM Studio/Ollama, MCP) that diagnoses failing Playwright/pytest runs and proposes fixes, zero API cost, full data privacy."
