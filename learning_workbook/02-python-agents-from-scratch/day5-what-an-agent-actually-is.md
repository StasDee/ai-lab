<div class="day-label">Day 5</div>

# Module 2, Day 5: What an Agent Actually Is

<p class="subtitle">~1.5-2 hrs | Difficulty: Beginner-Intermediate</p>

<div class="tldr-box">
<p><strong>TL;DR:</strong> An "agent" is not a new kind of model: it's a loop your code runs around an ordinary chat completion call. The model never does anything in the world; it only ever emits text. Your loop is what turns "the model said to call <code>run_pytest_suite</code>" into an actual subprocess running on your machine. Today is entirely conceptual (no code yet) because getting this mental model right first is what makes Day 6's implementation feel obvious instead of magical.</p>
</div>

<div class="objective-box">
<p><strong>Objective:</strong> By the end of today you can explain, precisely and from first principles, what happens between sending a prompt with tools attached and a tool actually running: at the wire level, the loop level, and the "why does this pattern exist at all" level. You'll also be able to explain why a badly-written tool description is a bug, not a documentation nitpick.</p>
</div>

## Theory

### From one round trip to a loop

Every call you made in Module 1 had the same shape: you sent `messages`, the server ran the token-prediction loop from Day 0 to completion, and you got text back. One request, one response, done. Nothing in that shape lets the model *do* anything: it can only describe, in words, what it would do.

An **agent** changes exactly one thing about that shape: alongside `messages`, you also send a list of **tools** the model is allowed to request. The model still only produces text, but now some of that text is a structured request to call one of those tools, and your code is watching for it.

The full cycle, usually called **ReAct** (Reason + Act, from the 2022 paper linked at the end of this lesson), looks like this:

1. Send the model `messages` **plus** `tools=[...]`
2. The model either answers directly, or asks to call a tool
3. Your code executes that tool call in the real world (read a file, run a command, hit an API)
4. The result goes back into the message history as new context
5. Repeat from step 1 (now with the tool result included) until the model gives a final answer instead of another tool call

Notice what's doing the "acting" here: not the model. **Your code** is the only thing in this entire system that touches a file, a shell, or a network socket. The model's contribution, every single time, is text. This distinction matters more than it sounds like it should: it's the answer to nearly every "wait, how is this secure / debuggable / testable" question you'll be asked about agents in an interview.

### Diagram: plain chat vs. the agent loop

<div class="diagram-wrap">

<img src="day5_loop.png" alt="Chat completion vs agent loop">

</div>
<p class="diagram-caption">Plain chat is a straight line. An agent is the same model call, wrapped in a loop with a decision point.</p>

The left side of the diagram is everything you did in Module 1. The right side adds exactly two new things: a **decision point** ("did the model ask for a tool, or is it done?") and a **feedback edge** (the tool's result flows back in as new input to the *same* model, in the *same* conversation). Everything else (the model itself, the API call shape, the `messages` list) is identical to what you already know.

### What actually crosses the wire

This is the part that removes the mystery. When you give the model `tools=[...]` and it decides to use one, the API response doesn't contain a function call in any executable sense. It contains a **JSON object matching a schema you provided**, something like:

```json
{
  "id": "call_abc123",
  "function": {
    "name": "read_file",
    "arguments": "{\"path\": \"config.yaml\"}"
  }
}
```

That's it. That's the entire "the model called a tool" event. `"function"` is a string the model predicted, token by token, because you told it (via the schema) that this string is a valid choice. `"arguments"` is a *second* string, itself JSON-encoded, that the model also predicted token by token, trying to match the parameter schema you gave it.

Your code then does three things nothing in the API does for you:

1. Looks up `"read_file"` in whatever mapping you've built (Day 6 calls this `DISPATCH`)
2. Parses `"arguments"` with `json.loads(...)` to get a real Python dict
3. Calls the actual Python function with those arguments, and captures whatever it returns

"Tool calling" support in an API, then, is really just this: **the model was fine-tuned to reliably produce that JSON shape when you hand it a schema**, instead of you having to regex a function call out of free-form prose. Every local runtime you set up in Module 1 (LM Studio, Ollama) implements this the same way, because they're all imitating the same OpenAI-originated wire format: which is exactly why the `tools=[...]` parameter you'll write on Day 6 needs zero changes to work against either one.

### Why tool descriptions are a reliability lever, not documentation

Here's the idea most people underrate the first time through this material. The `description` field on a tool isn't there for a human reading your code later: it's part of the **prompt**. The model reads it, every single turn, to decide (a) whether this tool is relevant right now and (b) what arguments to fill in.

Compare these two descriptions for the same function:

```json
{"name": "run_shell", "description": "gets file stuff"}
```

```json
{
  "name": "run_shell",
  "description": "Run a whitelisted shell command (pytest, git status, or ls) in the current project directory and return combined stdout/stderr.",
  "parameters": {
    "command": {"type": "string", "description": "One of: pytest, git status, ls"}
  }
}
```

The first description gives the model almost nothing to work with: it doesn't even indicate this tool runs commands rather than reading files. A model deciding whether to call it is guessing. The second tells the model exactly when to reach for this tool, what it's allowed to pass, and what shape the output will be. This isn't a stylistic preference: **a vague schema is a common, invisible root cause of "the agent isn't working."** It's not the model failing: it's the schema underspecifying the tool so badly that the model can't reliably decide when or how to use it. You'll see this concretely on Day 7 when you deliberately break a schema and watch the failure mode it produces.

### Why an agent needs a stopping condition at all

One detail that trips people up conceptually before they've written any code: what makes the loop *end*? The answer is entirely mundane: the model itself signals it. When the model's response has no `tool_calls` in it, that's the signal "I'm done, here's my answer." Your loop watches for that empty case on every iteration; it's the only exit condition that isn't a safety cap. Day 6 adds a second, harder exit condition (`max_iterations`) precisely because you can't fully trust the first one: a model can, and sometimes will, keep requesting tools indefinitely if nothing stops it.

## Practice

No code today: this is intentional. Before Day 6 turns this into a working loop, do these two things on paper:

1. **Annotate a real tool schema.** Take the `tools=[...]` shape from the OpenAI function-calling docs (linked below) and, next to each field (`name`, `description`, `parameters`, `required`), write one sentence on what information it gives the model versus what information it gives your code. You should end up with a clear split: some fields exist purely to guide the model's decision-making, others exist purely for your code to validate/execute against.

2. **Hand-trace one full loop iteration.** Pick a concrete scenario ("diagnose why `test_login.py` failed") and write out, turn by turn, what `messages` looks like before and after each of the 5 steps above. Include the actual JSON shape of the tool-call request and the tool-result message you'd append. Doing this by hand, without running any code, is what makes Day 6's implementation feel like typing out something you already understand rather than learning it for the first time.

## Common Pitfalls

- **Assuming the model "calls" the function.** It doesn't, ever. It predicts a string that looks like a function call. Every bug you'll debug in this module becomes easier once this is reflexive, not just known.
- **Treating the tool description as internal documentation.** It's read by the model on every turn: sloppy descriptions cost you reliability, not just readability.
- **Forgetting the loop needs an exit.** "No tool calls in the response" is the *intended* exit. Anything else (including a model that never stops) is what `max_iterations` exists to catch: you'll build that safety net tomorrow.
- **Conflating "tool calling support" with "the model is smarter."** It's a training-time change that makes the model good at emitting a specific JSON shape reliably, not a new capability layered on top of the same underlying next-token loop from Day 0.

## Assignment

Produce `docs/agent-loop-notes.md` containing:

1. The 5-step ReAct loop, in your own words (not copied from this lesson): written so you could recite it to an interviewer without notes
2. Your annotated tool schema from Practice step 1: which fields serve the model, which serve your code
3. Your full hand-traced example from Practice step 2: the `messages` list at each of the 5 steps, including the tool-call JSON and the tool-result message
4. One paragraph: why is a vague tool description a *reliability* bug and not just a style issue? Use your own example, not the `run_shell` one above.

## Why This Matters for Test Automation

Every diagnostic your Module 4 capstone performs (reading a failure log, re-running a suite, checking git history) is this exact loop, with test-automation-shaped tools standing in for `read_file`/`run_shell`. The reason this module insists on understanding the loop *before* building it is the same reason you wouldn't trust a test automation framework you can't explain: when a multi-step diagnostic session produces a wrong answer, "the loop reasoned about my failing test, called the wrong tool, and I can point to exactly which turn that happened on" is the difference between a debuggable system and a black box you're hoping works.

## Self-Check

- In one sentence, what does the model actually do when it "calls a tool": at the level of what crosses the wire?
- What are the two things that can legitimately end the loop, and which one is the *intended* one?
- Why does a tool's `description` field affect reliability, not just readability?
- If you handed your Practice step 2 trace to a colleague with zero context, could they follow it without asking you questions?

## Watch

"ReAct: Synergizing Reasoning and Acting in Language Models" (Yao et al., 2022): the paper this entire pattern is named after and built on: https://arxiv.org/abs/2210.03629

## Further Reading

- OpenAI function-calling guide (the schema shape most local runtimes imitate): https://platform.openai.com/docs/guides/function-calling

---

**Next:** Day 6, building the hand-rolled loop for real: the `DISPATCH` dict, `max_iterations` as a safety guard, and feeding errors back to the model instead of crashing.
