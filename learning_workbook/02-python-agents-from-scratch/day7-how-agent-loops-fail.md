<div class="day-label">Day 7</div>

# Module 2, Day 7: How Agent Loops Fail

<p class="subtitle">~1.5-2 hrs | Difficulty: Intermediate</p>

<div class="tldr-box">
<p><strong>TL;DR:</strong> Yesterday's loop works on the happy path. Today you break it on purpose, four different ways, so each failure mode is a recognized pattern instead of a surprise the first time it happens for real, likely mid-capstone, at the worst possible moment. Reproducing a bug deliberately, under controlled conditions, is a faster way to really understand it than reading about it ever is.</p>
</div>

<div class="objective-box">
<p><strong>Objective:</strong> By the end of today you've triggered and diagnosed all four core agent failure modes against your own Day 6 loop, and you have a written record (with real transcripts) of how you triggered each one, what it looked like, and what fixed it.</p>
</div>

## Theory

### Why "test the happy path" isn't enough for agents

In traditional test automation, you're used to the idea that a function's failure modes are mostly a function of its *inputs*: bad data, missing fields, wrong types. An agent loop has all of those, plus an entirely new category: failure modes caused by the **model's own non-deterministic output**, compounding across multiple turns. A schema that works fine on turn 1 of a conversation can start failing on turn 7, for reasons that have nothing to do with your code changing at all: only the *context* changed. This is genuinely new territory if your testing background is mostly deterministic systems, and it's worth sitting with why: the thing under test isn't a pure function anymore, it's a function whose behavior depends on an increasingly long, increasingly model-influenced conversation history.

### Diagram: four failure points, mapped onto the loop

<div class="diagram-wrap">

<img src="day7_failures.png" alt="Failure modes mapped onto the loop">

</div>
<p class="diagram-caption">Each failure mode attaches to a specific stage of Day 6's loop: not randomly, but at the exact point where something crosses a trust boundary.</p>

Notice the pattern in where these four failures sit: **every one of them happens at a boundary where text produced by the model has to become something else**, parsed data, an executed action, a decision to continue, or a signal the model itself has to correctly interpret. That's not a coincidence. It's the same lesson from Module 1's quantization discussion (tool-calling degrades faster than plain chat) showing up again at the loop level: anywhere structure is required, there's a place for structure to break.

### Failure 1: Malformed tool-call JSON

The model's `arguments` string is supposed to be valid JSON matching your schema. Usually it is. Occasionally (more often on a smaller or more aggressively quantized model, per Module 1) it isn't: a trailing comma, an unescaped quote inside a string value, a truncated response that got cut off mid-object. Day 6's `try/except` around `json.loads` already catches this without crashing, which means the *code* doesn't fail, but it's worth deliberately seeing what a malformed payload looks like and confirming the recovery path actually engages, rather than assuming it does.

### Failure 2: Hallucinated or wrong arguments

This is a different, sneakier problem: the JSON is **perfectly valid**, and the tool call **executes without error**, but the arguments are wrong. A model asked to read `config.yaml` might confidently pass `path="config.yml"` (wrong extension) or invent a path that was never mentioned anywhere in the conversation. `json.loads` succeeding tells you nothing about whether the *content* is trustworthy. This is why Day 6's Common Pitfalls flagged "trusting parsed arguments without validating them": this failure mode is exactly what that warning was about, and it's the one your `try/except` block does **not** protect you from.

### Failure 3: Infinite tool-calling loops

Nothing about the ReAct cycle logically terminates on its own (Day 6's Theory covered why `max_iterations` exists). This failure mode is what happens when that guard is the *only* thing standing between a working agent and one that burns through your CPU budget forever: a model that keeps deciding "one more tool call" is warranted, turn after turn, often because a tool result didn't actually contain the information it needed and it keeps trying slightly different ways to get it.

### Failure 4: Ignored tool results

The subtlest of the four, and the one that looks the least like a "failure" at first glance: the model asks the same question again, almost verbatim, after you've already answered it. This is rarely the model "being difficult": it's much more often a signal that **your tool result format is hard for the model to use**. A tool that returns a wall of unstructured log text, or a result that's technically correct but doesn't obviously answer the question asked, can produce exactly this behavior. Treat repeated near-identical tool calls as a data point about your tool's output shape, not about the model's competence.

## Practice

Work through all four failure modes against your Day 6 `run_agent()`. For each one, capture the actual `messages` transcript (not a paraphrase) as your evidence.

1. **Reproduce Failure 1 (malformed JSON).** The cleanest way: temporarily lower `temperature` to a high value like `1.2` (Module 1's Day 3 covered why this increases nondeterminism) on a smaller/more aggressively quantized model if you have one loaded, and run a prompt requiring a tool call with several string arguments. If your Q4_K_M 7B model refuses to produce a malformed payload no matter what (a good sign for that model!), simulate it directly: hand-write a broken `arguments` string and feed it straight into your parsing code to confirm the `except` branch behaves as expected.
2. **Reproduce Failure 2 (wrong arguments).** Ask your agent to read a file using a name that's *close to but not* an actual file in your directory (e.g., ask about `readme.md` when the real file is `README.md`). Watch whether the model passes the wrong-cased path straight through, and observe what `read_file` does with it (a `FileNotFoundError`, caught by your `except`, but note this is Failure 2 producing a Failure-1-shaped symptom, which is itself worth noticing).
3. **Reproduce Failure 3 (infinite loop).** Temporarily set `max_iterations=100` (never do this in anything other than a controlled test) and give the agent a prompt designed to be unanswerable from your current tools: e.g., ask it something requiring a tool you didn't define. Watch how many turns it takes before it either gives up gracefully or you have to stop it manually. Then set `max_iterations` back down and confirm the guard now cuts it off cleanly.
4. **Reproduce Failure 4 (ignored results).** Make `read_file` return an unhelpfully vague result on purpose (e.g., truncate it to the first 20 characters) for a question that genuinely needs the full content. See whether the model asks again, rephrased, rather than working with what it got.

## Common Pitfalls

- **Assuming a caught exception means the failure mode is "handled."** Day 6's `try/except` prevents a *crash*: it does not mean the underlying failure (wrong argument, bad reasoning) has been fixed. Catching the symptom isn't the same as addressing the cause.
- **Blaming the model for Failure 4 instead of your tool's output shape.** This is the single most common misdiagnosis. Before concluding "the model isn't smart enough," check whether your tool result actually contains a clear answer to what was asked.
- **Only testing with `max_iterations` already generous.** If you never turn it down, you'll never actually see the guard engage, and "I assume it works" isn't the same as having watched it work.
- **Reproducing a failure once and calling it understood.** Nondeterminism (Module 1, Day 3) means a single run proves a failure mode is *possible*, not that you've seen its full range. Re-run at least twice per failure mode.

## Assignment

Produce `docs/failure-modes-day7.md` with one entry per failure mode (four total), each containing:
1. Exactly how you triggered it (prompt, temperature, any code changes)
2. The relevant `messages` transcript excerpt showing the failure
3. What (if anything) you changed afterward, and why (a fix, a mitigation, or "this is inherent and here's how the current guard handles it")

## Why This Matters for Test Automation

This is, in miniature, exactly the instinct that makes someone good at traditional test automation: don't wait for production to teach you your system's failure modes, go find them yourself under controlled conditions. The difference here is the failure surface: instead of edge-case inputs, you're probing where non-deterministic model output meets deterministic code. Being able to say "I've seen all four core agent failure modes firsthand, reproduced on purpose, and here's what each looks like" is a materially stronger interview answer than reciting the four categories from memory without ever having triggered one.

## Self-Check

- Name two concrete ways your loop could infinite-loop, and how you guard against each.
- Why does Failure 2 (wrong arguments) slip past Day 6's `try/except`, while Failure 1 (malformed JSON) doesn't?
- If a model keeps re-asking a question you've already answered, what's the first thing you should inspect: the model's reasoning, or your tool's output format? Why?
- Which of the four failure modes would you expect to get *worse* under more aggressive quantization, based on Module 1's Day 1 material, and why?

---

**Next:** Day 8, the framework pass. Rebuild this same capability with smolagents and see precisely what a framework buys you, and what it quietly hides.
