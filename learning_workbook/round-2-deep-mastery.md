# Round 2: Deep Mastery
### Production-Grade Agentic AI for Test Automation

**Goal:** Move from "I built a working demo" to "I can design, secure, and operate an agentic system in production."
**Pace:** Self-paced, roughly 8-10 weeks following Round 1.
**Hardware:** i5, 64GB RAM, no GPU: CPU-only inference throughout.

---

## Weeks 1-2: Multi-Agent Orchestration
- [ ] Learn LangGraph or CrewAI
- [ ] Build a planner / executor / analyst pipeline around Playwright MCP: one agent breaks down the testing goal, one drives the browser, one triages failures
- [ ] Compare this against your Round 1 single-agent loop: document where multi-agent actually earns its complexity, and where it doesn't

## Weeks 3-4: RAG for QA Knowledge
- [ ] Stand up ChromaDB with local embeddings
- [ ] Ground your agent's test generation in real specs/requirements docs, not just the failure log
- [ ] Evaluate retrieval quality, not just generation quality

## Weeks 5-6: Evaluation & Observability
- [ ] Self-host Langfuse to trace the full agent loop: every tool call, every model decision
- [ ] Add RAGAS-style checks for output quality (accuracy, relevance, hallucination rate)
- [ ] Turn this into a dashboard or report you could hand to a team lead

## Week 7: Security
- [ ] Sandbox your MCP servers in Docker
- [ ] Apply zero-trust principles to tool execution: least privilege, input sanitization
- [ ] Build a defense against prompt injection from untrusted content (logs, scraped pages, test output)

## Week 8: Bigger Models, Same Box
- [ ] Try Qwen3-Coder-30B-A3B: a mixture-of-experts model (30B total params, ~3B active per token) that fits in 64GB RAM at Q4 and can run notably faster than a dense model of similar size on CPU
- [ ] Benchmark it against your Round 1 dense 7B model on the same tasks
- [ ] Document when the bigger model is worth the extra load time and when it isn't

## Weeks 9-10: CI/CD Integration & Capstone 2
- [ ] Wire the full multi-agent system into GitHub Actions so it triages failing tests on every PR
- [ ] Write it up as a short blog post or LinkedIn piece: this is the credential; the writeup is what makes the work visible to a hiring manager
- [ ] Update your CV bullet to reflect production concerns: multi-agent design, observability, security, RAG-grounded generation

---

## What This Round Proves in an Interview
- You can reason about when multi-agent complexity is worth it, not just build it
- You understand evaluation as a discipline, not an afterthought
- You've thought about security for a system that can execute code and touch real infrastructure
- You can make hardware/model trade-offs explicit and back them with your own benchmarks
