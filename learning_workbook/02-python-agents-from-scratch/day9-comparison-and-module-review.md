# Day 9

## Module 2, Day 9: Comparing Your Two Agents, and Module Review

<p class="meta-line">~1.5-2 hrs | Difficulty: Intermediate</p>

<div class="tldr-box">
<strong>TL;DR:</strong> You've now built the same agent capability twice: by hand on Day 6, through smolagents on Day 8. Today you don't write a third version. You put both side by side and extract the actual engineering judgment: what each approach costs you, what it quietly hides from you, and how well each holds up when something breaks for real (including the smolagents timeout you're chasing this week). You'll close the day with your first real ADR-style <code>decisions.md</code> entry and a full recap of Module 2.
</div>

## Objective

<div class="objective-box">
By the end of today you can explain, from firsthand experience rather than received wisdom, when hand-rolling an agent loop is the right call and when reaching for a framework is; and you have that judgment written down in a form you can point back to later: in your capstone's <code>architecture.md</code>, in an interview, or in your own memory eight months from now when you've forgotten the details.
</div>

## Theory

### 1. Why a "comparison day" is its own skill

Most tutorials teach a thing once, with one approach, and move on. That leaves you with an opinion, not a judgment. An opinion is "I like frameworks" or "I like doing it myself." A judgment is "I hand-roll when X, I reach for a framework when Y, and here's the specific cost I'm trading away either direction." Interviewers can tell the difference in about one follow-up question; and so can you, six months into a job, when the codebase you inherited made the opposite choice from the one you'd have made and you need to work with it anyway.

Today is deliberately not a coding day. You already have both implementations working. The work now is comparison, and comparison is a discipline you'll reuse constantly in this field: hand-rolled vs. framework today, later it'll be Playwright vs. Selenium, pytest vs. a custom test runner, self-hosted vs. managed infra. The muscle you're building is the same one every time: name the axes, test both under real conditions, write the decision down.

### 2. Two implementations, one capability, side by side

Quick recap so both are fresh in view. Same task (call a tool, get a result, answer), two different amounts of code standing between you and it.

**Hand-rolled (Day 6, `run_agent`):**

```python
def run_agent(user_prompt: str, max_iterations: int = 6):
    messages = [{"role": "user", "content": user_prompt}]

    for _ in range(max_iterations):
        response = client.chat.completions.create(
            model="qwen2.5-coder-7b-instruct",
            messages=messages,
            tools=tools,
        )
        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            return msg.content

        for call in msg.tool_calls:
            fn_name = call.function.name
            try:
                args = json.loads(call.function.arguments)
                result = DISPATCH[fn_name](**args)
            except Exception as e:
                result = f"Error executing {fn_name}: {e}"
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": str(result),
            })

    return "Max iterations reached without a final answer."
```

**Framework (Day 8, smolagents):**

```python
agent = ToolCallingAgent(tools=[read_file], model=model)
result = agent.run("Read config.yaml and summarize what it configures.")
```

Same capability. Roughly 30-40 lines versus roughly 2. That gap (everything smolagents is doing in the space between those two lines) is exactly what the rest of today interrogates. It isn't free; it's just paid for somewhere you can't see from the call site.

### 3. Axis 1: Lines of code, and what they're actually buying you

The naive read of "40 lines vs. 2 lines" is "the framework is just better." That's true only if the 38 lines you didn't write were pure boilerplate with no decisions embedded in them. They aren't. Look at what's compressed into that one `agent.run()` call:

- How many iterations to attempt before giving up (your `max_iterations=6`; smolagents has its own default, which you didn't choose)
- What happens when `json.loads()` fails on a malformed tool call (your explicit `try/except`; smolagents has its own internal handling, which you haven't read)
- Whether a failed tool call gets retried, fed back as an error, or raised (your choice, in your `except` block; smolagents' choice, somewhere in its source)
- The exact shape of what gets appended to conversation history after a tool result

Fewer lines doesn't mean fewer decisions: it means the decisions were already made, by someone else, and shipped as defaults. Sometimes those defaults are exactly what you'd have chosen. Sometimes they aren't, and you won't find out until a run behaves in a way you didn't expect.

### 4. Axis 2: Visible vs. hidden: retries, iteration caps, message bookkeeping

This is the sharpest way to see the trade-off. In `run_agent`, every one of the following is a line you wrote and can point to:

```
max_iterations=6                          <- the safety cap, your number
except Exception as e: result = f"..."    <- your error-handling policy
messages.append({"role": "tool", ...})    <- the exact history-append shape
```

In the smolagents version, all three of those exist too (they have to, the loop can't function without them) but they live inside the library, not your file. `ToolCallingAgent` has its own default step limit, its own internal retry/parsing behavior for tool calls, and its own convention for what gets added to its internal message state after a tool executes. None of that is wrong. It's tested, it's used by thousands of other people, and it's very likely more battle-hardened than the `except Exception` you wrote in twenty minutes on Day 6.

But "more battle-hardened" and "known to you" are different properties. You can answer "what happens on iteration 7" for your hand-rolled loop instantly, from memory, because you wrote the number. For smolagents, that answer lives in a source file you'd have to go find. Day 8's Self-Check already asked you this directly: "what's now invisible to you that was visible in the hand-rolled version?" And today is where that question gets a real answer instead of a hand-wave.

### 5. Axis 3: Debuggability when something actually breaks

This is the axis with the highest stakes, and you don't have to imagine an example: you're living one right now. The 400 `"terminated"` response you've been chasing this week, ~417 seconds into a smolagents `ToolCallingAgent` run, is a textbook illustration of exactly what this axis is about.

With the hand-rolled loop, a hang or malformed response shows up as a stack trace pointing at a specific line in `run_agent`: you know immediately whether the problem is your JSON parsing, your dispatch, or the raw response from `client.chat.completions.create()`, because there's nothing else it could be. Three layers, all yours, all inspectable with a `print()` or a debugger breakpoint.

With smolagents in the loop, the same failure has more possible addresses: your prompt, the tool schema you defined, smolagents' internal step/retry logic, `OpenAIServerModel`'s translation into the API call, or the model/runtime itself (LM Studio, in your case, and specifically whichever GGUF is loaded). Your current diagnostic step (swapping to Qwen2.5-Coder-7B-Instruct to isolate whether the failure is model-specific or script-specific) is the correct move precisely *because* the framework adds that ambiguity. You're not debugging "my code." You're debugging "my code, or the framework's assumptions about my code, or the model, or the server," and the swap-the-model test is how you start cutting that search space down. That extra step is the real, concrete cost of Axis 2's hidden bookkeeping. It isn't abstract.

None of this means smolagents is the wrong choice. It means: **the moment something breaks, a framework doesn't remove complexity, it relocates it**, out of your file and into a dependency you now have to reason about under time pressure. Whether that trade is worth it depends entirely on how well-tested the framework's hidden path is versus how well you understand your own.

### 6. Axis 4: Where frameworks earn their complexity: coordination

So far this reads like a case for always hand-rolling. It isn't: there's a real point where the trade flips, and it's worth naming now even though you won't hit it until Round 2.

A single agent talking to itself in a loop, calling tools one at a time, is exactly the shape your hand-rolled version handles well. The moment you have *multiple* agents that need to hand work to each other (a planner deciding what to do, an executor doing it, an analyst checking the result, as previewed in `round-2-deep-mastery.md`'s multi-agent module), the bookkeeping problem stops being "track one conversation history" and becomes "track N conversation histories, plus the handoff protocol between them, plus what happens when one agent's failure should or shouldn't propagate to another." That's where LangGraph's explicit state-graph model, or CrewAI's role-based orchestration, earns its keep: the coordination logic is exactly the kind of thing you *want* to be someone else's well-tested problem, because hand-rolling it correctly is genuinely hard and the failure modes are non-obvious.

The pattern to notice: frameworks are worth their opacity in proportion to how much genuinely hard, already-solved coordination logic they're taking off your plate. For a single ReAct loop, that logic is simple enough that hand-rolling it yourself costs little and teaches you a lot. For multi-agent orchestration, hand-rolling it yourself costs a great deal and teaches you mostly how easy it is to get subtly wrong.

### 7. Axis 5: Interview defensibility

Here's the version of this you should be able to say out loud, unscripted, the way Day 3 gave you a one-liner for streaming vs. non-streaming:

> "I hand-roll an agent loop first, even when I know I'll end up using a framework, because it's the only way to actually know what the framework is doing for me. For a single-agent diagnostic tool like my capstone, hand-rolled is often the right *production* choice too, not just a learning exercise: it's fewer moving parts to debug under time pressure, and every failure mode is visible in my own code. I'd reach for a framework once I have multiple agents that need to coordinate, or once I'm working with a team where a shared, well-known abstraction is worth more than the transparency I'd be giving up."

That answer works because it's specific and it names a real cost on both sides: it isn't "frameworks are for people who don't understand the fundamentals" (dismissive, and wrong) and it isn't "always use the framework, it's more efficient" (true of typing speed, not necessarily true of debugging time). A senior-level answer names the axis the decision actually turns on.

### 8. A decision framework you can reuse

Reduced to a checklist you can actually apply next time, not just for this project:

| Lean hand-rolled when... | Lean framework when... |
|---|---|
| Single agent, no coordination needed | 2+ agents need to hand off work to each other |
| You need to see the exact wire behavior to debug | The pattern is well-established and you trust the library's testing more than your own |
| Small, stable tool set (a handful of functions) | Large or frequently-changing tool set where boilerplate reduction compounds |
| Learning or teaching context: understanding matters more than speed | Team already has shared familiarity with the framework |
| The task is core to what you're shipping (worth owning fully) | The task is incidental: you'd rather not own its edge cases |

Notice this isn't "hand-rolled is for beginners, frameworks are for production." Your own capstone is the counter-example: a single-agent diagnostic loop, hand-rolled, is a legitimate production architecture, not a stepping stone you graduate out of.

<div class="diagram-block">
<img src="stacks.png" alt="Hand-rolled vs framework call stack comparison">
<p class="diagram-caption">Same capability, different amount of it living in code you can read directly</p>
</div>

### 9. From comparison to a decision: writing the ADR

An ADR (Architecture Decision Record) is a short, standard shape for writing a decision down so it survives past the moment you made it: **Context** (what situation forced a choice), **Decision** (what you picked), **Consequences** (what you're accepting as a trade-off, both good and bad). This is the exact pattern `decisions.md` is for, and today's is your first real entry, not a placeholder.

<div class="adr-box">
<strong>ADR template for today's entry:</strong>

```
## ADR-002: Hand-rolled agent loop vs. smolagents for the capstone

Date: [today's date]

### Context
Module 2 built the same tool-calling agent loop two ways: hand-rolled
(Day 6) and via smolagents' ToolCallingAgent (Day 8). The capstone
(Module 4) needs one of these as its actual architecture, not both.

### Decision
[Which one you're carrying forward, stated plainly]

### Consequences
- What you gain by this choice:
  [e.g. full visibility into failure modes; no dependency on smolagents'
  internal retry/step-limit behavior; a debugging story you fully own]
- What you give up:
  [e.g. more code to maintain yourself; no free upgrade path to
  smolagents' future fixes/improvements]
- What would change this decision later:
  [e.g. if the capstone grows into a multi-agent system in Round 2,
  revisit: this ADR is scoped to the single-agent capstone specifically]
```
</div>

Fill in the bracketed parts with your actual answer, informed by today's Practice exercise below, not decided in the abstract. An ADR that was written before you actually timed the debugging difference isn't evidence of judgment, it's a guess with a template around it.

### 10. Module 2's arc, in one line each

<div class="diagram-block">
<img src="module2arc.png" alt="Module 2 arc from Day 5 to Day 9">
<p class="diagram-caption">Each day added one layer to the same underlying idea: a loop, made real, then made to fail on purpose, then compared honestly</p>
</div>

You'll see this arc again in the full Module 2 Review section near the end of today's lesson.

## Practice

**Step 1: Side-by-side diff.** Open `src/agent_loop.py` (Day 6) and `src/agent_smolagents.py` (Day 8) in split view. For each of the following, write one line noting which file it lives in and how many lines it takes: the iteration cap, the tool-call JSON parsing, the error-handling policy, the final message returned to the caller. This is the raw material for Axis 1 and Axis 2 above. Don't skip straight to the write-up.

**Step 2: Time-to-debug, deliberately broken.** Reproduce one failure in each version and time yourself, stopwatch or just a timestamp, from "I noticed something's wrong" to "I know exactly which line/layer is responsible" (not fixed yet, just diagnosed):
   - Hand-rolled: rename one entry in `DISPATCH` so a tool call fails to resolve.
   - Framework: pass a malformed `@tool`-decorated function (drop the docstring, per Day 8/Module 2's schema-generation requirement) and run the same prompt.

Note both times. This is real data, not a guess; and it's the same category of exercise as the model-swap test you're running on your live smolagents issue this week.

**Step 3: Write the comparison table.** Using Steps 1-2, fill in: lines of code (rough count), time-to-diagnose (from Step 2), what surprised you about what the framework hid, and your own one-line version of the Axis 5 interview answer: write it in your own words, not copied from Theory above.

**Step 4: Write your ADR-002 entry.** Use the template in Theory section 9. This is not optional busywork: it's the actual deliverable this whole day has been building toward, and it's the entry you'll reference directly when you write `architecture.md`'s "Alternatives Considered" section in Module 4.

## Common Pitfalls

<div class="pitfall-box">

- **Comparing apples to oranges.** If your hand-rolled version has three tools and your smolagents version has one, your lines-of-code and debugging-time numbers aren't measuring the framework: they're measuring the task size. Keep the tool set identical across both before you compare anything.
- **Counting only surface lines of code.** 2 lines vs. 40 looks like a landslide until you count the decisions embedded in the 2, not just the characters. Revisit Axis 1 before you let a raw LOC number drive your ADR.
- **Treating "hidden" as automatically "worse."** Smolagents' internal retry logic is very likely more correct than a first-pass `except Exception` block you wrote in twenty minutes. Hidden isn't the same as bad: it's the same as *unverified by you*. Say that precisely in your write-up, not "frameworks are risky."
- **Writing the ADR before doing the Practice exercise.** An architecture decision that isn't backed by your own timed data is an opinion wearing a template. Do Steps 1-3 first.
- **Presenting the choice as universal in an interview.** "I always hand-roll" or "I always use a framework" is a weaker answer than "here's the specific axis this decision turned on for this project." Interviewers are listening for the axis, not the verdict.
- **Skipping the "what would change this decision" line in the ADR.** This is the line that shows you understand the decision is scoped to current conditions, not a permanent belief, exactly the kind of thing a good follow-up question will probe.

</div>

## Why This Matters for Test Automation

This exact judgment call (build it yourself vs. adopt an existing framework) is one you'll make constantly in test automation, and it's usually evaluated in interviews under a different name: Selenium vs. Playwright, a custom test runner vs. pytest plugins, a hand-rolled reporting pipeline vs. Allure. The underlying question is always the same shape as today's: what does the existing tool hide from me, is that hiding a net positive given how well-tested it is, and what's my actual debugging cost when it breaks in a way the tool's authors didn't anticipate? A senior QA engineer who can only say "I use Playwright because it's modern" hasn't demonstrated judgment. One who can say "I use Playwright's auto-waiting because hand-rolling reliable waits is a well-known source of flaky tests, but I still read its retry-timeout defaults before trusting them in CI" has demonstrated exactly the skill this day is building.

## Assignment

Produce `docs/framework-comparison.md` containing:

1. The comparison table from Practice Step 3 (lines of code, time-to-diagnose per version, what surprised you)
2. A short paragraph per axis (1 through 5 from Theory) written in your own words, not restating the lesson, applying it to what you actually observed in your two files
3. Your one-line interview answer from Practice Step 3, written the way you'd actually say it out loud

And your first real `decisions.md` entry:

4. ADR-002, filled in from the template in Theory section 9: Context, Decision, Consequences, and the "what would change this" line

## Module 2 Review

What connects across all five days:

- **Day 5** gave you the mental model: an agent is a loop, not a single call, and the model never "does" anything outside your code: it only ever emits text your code decides how to act on.
- **Day 6** turned that model into working code you fully own: `run_agent`, `DISPATCH`, an explicit `max_iterations` guard: every failure mode traceable to a specific line.
- **Day 7** broke that code on purpose: malformed JSON, hallucinated arguments, infinite loops, ignored tool results, so those failure modes are recognized patterns now, not surprises the first time you meet them for real.
- **Day 8** rebuilt the identical capability through smolagents, trading visible code for a tested, compact abstraction, and left you with a concrete question about what that trade actually costs.
- **Day 9** (today) answered that question with real data instead of a guess, and turned the answer into your first ADR, the same documentation-as-artifact pattern you'll keep using through the capstone.

You now have two working agent implementations, a timed comparison between them, and a written, defensible decision about which one is real architecture for your capstone, not just "the one I built more recently."

## Self-Check

- What actually happens on the wire when either version's model "calls a tool": can you describe it identically for both, since the underlying API call doesn't change?
- Why is tool description/docstring quality a reliability lever in *both* versions, not just the hand-rolled one?
- Name two concrete ways either loop could infinite-loop, and how each version guards against it: are the guards the same, or different in a way that matters?
- What's now invisible to you in the smolagents version that was fully visible in the hand-rolled one, and can you name where in the library source you'd go look, if you needed to?
- If a teammate asked you "why didn't you just use the framework everywhere," what's your answer, using the axis language from today, not a general preference?
- Looking at your ADR-002: what specific future condition would flip your decision, and would you actually notice if that condition occurred?

## External Links

- smolagents docs: https://huggingface.co/docs/smolagents/index
- ReAct paper (Yao et al.): https://arxiv.org/abs/2210.03629
- Michael Nygard's original ADR pattern (the template Theory section 9 is based on): https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- LangGraph docs (Round 2 preview): https://langchain-ai.github.io/langgraph/
- CrewAI docs (Round 2 preview): https://docs.crewai.com

---

<p class="next-line">Next: Day 10, What MCP Solves. You've hand-rolled tool execution and compared it against a framework; now you plug into the standard that lets any agent use any tool, including ones the QA industry already ships.</p>
