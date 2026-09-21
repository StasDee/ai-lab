<div class="day-label">Day 8</div>

# Module 2, Day 8: The Framework Pass

<p class="subtitle">~1.5 hrs | Difficulty: Intermediate</p>

<div class="tldr-box">
<p><strong>TL;DR:</strong> Today you rebuild Day 6's exact capability using smolagents, a lightweight agent library from Hugging Face: same tools, same local model, far less code. The point isn't that the framework is "better." It's that you now know precisely what those saved lines were doing, because you wrote them yourself first, which means you can name exactly what the framework is buying you and exactly what it's hiding.</p>
</div>

<div class="objective-box">
<p><strong>Objective:</strong> By the end of today you have a working smolagents version of Day 6's agent, and you can list (specifically, not vaguely) what's now invisible to you that was visible in your hand-rolled version.</p>
</div>

## Theory

### Why hand-roll first was the right order

You'll reach for a full orchestration framework (LangGraph, CrewAI) in Round 2, once you have multiple agents that genuinely need to coordinate. That's the right call *then*. Doing the hand-rolled version first, before touching any framework, front-loads three things that are much harder to get later:

- **You can debug a broken agent instead of guessing which framework abstraction is misbehaving.** When Day 7's Failure 2 happens inside a framework's internals, you're debugging someone else's retry logic, not your own loop.
- **You can answer "what does your agent actually do" precisely**, instead of "the framework handles it", a real difference in how that answer lands in an interview.
- **You know exactly what a framework is buying you**, because you've personally felt the boilerplate it removes, today's lesson, concretely, rather than a claim you're taking on faith.

### What smolagents actually replaces

Look back at Day 6's `run_agent()`. Strip it down to its actual responsibilities: (1) hold and grow a `messages` list, (2) call the API with `tools=[...]` attached, (3) parse the response and detect tool calls versus a final answer, (4) look up and execute the right function, (5) format the result back into the message list correctly, (6) loop, capped by `max_iterations`. Every one of those six responsibilities is still happening when you use smolagents: it's just that `ToolCallingAgent` is now doing all six *for* you, behind a two-line `agent.run(prompt)` call.

```python
from smolagents import ToolCallingAgent, tool
from smolagents import OpenAIServerModel

@tool
def read_file(path: str) -> str:
    """Read the contents of a text file at the given relative path.

    Args:
        path: Relative path to the file.
    """
    with open(path, "r") as f:
        return f.read()[:4000]

model = OpenAIServerModel(
    model_id="qwen2.5-coder-7b-instruct",
    api_base="http://localhost:1234/v1",
    api_key="not-needed",
)

agent = ToolCallingAgent(tools=[read_file], model=model)
result = agent.run("Read config.yaml and summarize what it configures.")
```

Two design choices worth noticing immediately, because they map directly onto Day 5-6 concepts you already understand:

**The `@tool` decorator replaces your manual `tools=[...]` dict.** It reads the function's docstring and type hints and *generates* the JSON schema for you: the same schema you hand-wrote for `read_file` on Day 6. This is convenience, not magic: the schema still has to be just as precise as Day 5 insisted, it's just that smolagents derives it from your docstring instead of you writing the JSON by hand. A vague docstring here produces exactly the same reliability problem a vague hand-written `description` field did.

**There's no visible `DISPATCH` dict, no visible loop, no visible `max_iterations` in your code.** They still exist (inside the library); you just don't see them.

### Diagram: what's stacked underneath `agent.run()`

<div class="diagram-wrap">

<img src="day8_layers.png" alt="Layered stack: what smolagents hides">

</div>
<p class="diagram-caption">Two new layers appear on top of everything you already built. The bottom two are unchanged from Day 6 and Module 1.</p>

Read this bottom-to-top: the `openai` client call is identical to what you've used since Module 1, Day 3. Your Day 6 loop's *concepts* (dispatch, parsing, iteration limits) still exist: they're just now implemented inside smolagents rather than in your file. The genuinely new layer is the top one: retry logic, message formatting conventions, and iteration limits that smolagents chose for you, using defaults you didn't write and, by default, can't see without reading the library's source.

### What's now hidden, specifically

Being precise here is the actual point of today, not a throwaway line:

- **Exact retry behavior.** If a tool call fails, does smolagents retry automatically? How many times? With what backoff, if any? Day 6 made this an explicit, visible choice (feed the error back as a tool result, let the model decide). smolagents has *some* answer to this, but it's not sitting in your file where you can read it at a glance.
- **How many iterations it silently attempts before giving up.** There's an equivalent to `max_iterations` in there somewhere, with its own default. Unless you've gone looking, you don't know what it currently is for your setup.
- **The exact prompt/message formatting it uses internally.** Your Day 6 loop's `messages` list is exactly what you wrote. smolagents may reformat, prepend system instructions, or restructure things in ways that affect how the model behaves, invisibly, from your code's point of view.

None of this makes smolagents worse: it makes it a genuine trade: less code to write and maintain, in exchange for less visibility into exactly what's happening on a bad run. That trade is *fine* to make, especially once you're confident the underlying loop behaves the way you expect, which is precisely why Day 6 came first.

## Practice

1. Rebuild Day 6's identical capability, same tools (`read_file`, `run_shell` or your adapted equivalents, plus your Day 6 custom tool), same local model, using smolagents.
2. Run the exact same prompts you used in Day 6 and Day 7's Practice sections against this version. Compare the final answers.
3. Deliberately re-run Day 7's Failure 3 setup (a prompt requiring a tool you haven't defined) against the smolagents version. Does it behave the same as your hand-rolled loop's `max_iterations` cutoff, or differently? Note exactly what you observe: an error message, a silent stop, a different number of attempts.
4. Try to find smolagents' actual default iteration limit and retry behavior (its documentation, linked below, or its source directly). Write down what you find: this converts "invisible to me" into "invisible by default, but I know where to look."

## Common Pitfalls

- **Assuming "less code" means "the problem got simpler."** The problem (reliable tool-calling over a growing conversation) is exactly as hard as it was on Day 6. The framework just took ownership of solving it, on your behalf, with its own defaults.
- **Never actually looking up what the framework's defaults are.** "I don't know and haven't checked" is a materially weaker position than "I checked, and here's what smolagents does by default", even if the answer to both questions is functionally similar day-to-day.
- **Comparing apples to oranges.** If your Day 6 loop and your Day 8 smolagents version behave differently on the same prompt, check whether that's a *meaningful* difference (different retry/formatting behavior) before assuming one of them is "wrong."
- **Skipping the docstring quality bar.** The `@tool` decorator generating a schema from your docstring doesn't lower the bar Day 5 set for tool descriptions: it just moves where you write the description.

## Assignment

Produce `src/agent_smolagents.py`: a working smolagents rebuild of Day 6's `agent_loop.py`, using the same tool set, tested against the same prompts. Alongside it, add a short `docs/framework-comparison-notes.md` (rough notes only, Day 9's assignment formalizes this) capturing what you found when you looked up smolagents' default iteration limit and retry behavior.

## Why This Matters for Test Automation

"When do you reach for a framework versus hand-roll it" is a question senior engineers get asked constantly, in agentic AI contexts and well beyond them: it's really a question about judgment, not familiarity with any particular library. The strongest possible answer isn't "frameworks are better" or "always build it yourself": it's what you're building toward today: a specific, evidence-based account of what a given framework buys you and what it costs you, for *this* task, at *this* scale. That's a directly transferable answer to "why did your team choose [ORM / test framework / CI tool] X over Y" in any interview, not just an agentic-AI-specific one.

## Self-Check

- What's now invisible to you that was visible in your Day 6 hand-rolled version? List at least three specific things, not a general "the framework handles it."
- Does the `@tool` decorator change *what* makes a good tool description, or just *where* you write it?
- If Day 7's Failure 3 (infinite loop) happened inside the smolagents version in production, how would your debugging process differ from debugging it in your Day 6 loop?
- Based on what you found in Practice step 4, what is smolagents' actual default behavior for iteration limits, and were you right or wrong about what you expected it to be?

## External Links

- smolagents docs: https://huggingface.co/docs/smolagents/index

---

**Next:** Day 9, Module 2 review. Consolidate the hand-rolled-vs-framework decision into a real engineering answer, and close out everything this module built.
