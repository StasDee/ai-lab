<div class="day-kicker">Day 14</div>

<h1 class="doc-title">Module 3, Day 14: Schema Design & Module Review</h1>

<div class="subtitle">~1.5-2 hrs | Difficulty: Intermediate</div>

<div class="tldr-box">

**TL;DR:** No new mechanics today: this is where Module 3's four days of hands-on work get consolidated into house rules you can apply without re-deriving them, and reviewed until you can answer for any of it from memory, not notes. You'll merge Module 2's tool-description lesson with Day 12's MCP-specific version into one schema-design checklist, put your own Day 12 docstrings through the "total stranger" test for real, write your first genuine `decisions.md` entry, and walk the full arc from Day 10's diagrams to Day 13's working client as one continuous idea.

</div>

## Objective

<div class="objective-box">

By the end of today you have one consolidated set of schema-design house rules you can apply to any future tool without relearning the reasoning each time; you've rewritten your Day 12 docstrings against that checklist and gotten a second opinion on them; you've written a real ADR-style `decisions.md` entry justifying stdio over HTTP for this project; and you can answer Module 3's full self-check set (Days 10 through 13) without looking anything up.

</div>

## Theory

### 1. Two lessons that were always the same lesson

Module 2.2 told you tool descriptions are a reliability lever, not documentation. Day 12 told you a docstring is the schema, mechanically, via `@mcp.tool()`'s introspection. These were never two separate lessons: Day 12 just removed the last bit of distance between "writing a good description" and "writing correct code," because under MCP there's no longer a separate schema file that could theoretically diverge from your docstring. They're the same artifact. Today's job is to fold both into one checklist you can run against any tool, whether it's a Module 2 `tools=[...]` entry or an MCP `@mcp.tool()` docstring, the underlying discipline doesn't change based on which mechanism is reading it.

### 2. House rules for a schema that survives contact with a stranger

Each rule below exists because of something specific you already watched go wrong (or watched work) earlier in this workbook. That's deliberate: a rule with a memorable failure case attached to it survives longer than a rule stated in the abstract.

**Rule 1: The description answers "when," not just "what."** "Runs the pytest suite" describes what the tool does; it says nothing about when a model should reach for it versus `get_last_failure_log`. Compare:

| Weak | Strong |
|---|---|
| `"""Runs tests."""` | `"""Run the pytest suite at the given path and return the raw output. Use this to execute or re-run tests; use get_last_failure_log instead if you only need to inspect a previous run's log without re-executing anything."""` |

The strong version does real work: it disambiguates this tool from its nearest neighbor, which is exactly the kind of confusion a model with two similarly-named, vaguely-described tools will otherwise resolve by guessing.

**Rule 2: Every parameter description states its shape, not just its name.** `test_path: Relative path to the test directory or file` tells a model two things a bare parameter name doesn't: that the path is relative (to what?: worth stating explicitly if it's not obvious, per today's Common Pitfalls) and that it can point at either a file or a directory. A parameter description that just repeats the parameter name (`"""path: the path"""`) provides zero information beyond what the name already said.

**Rule 3: State what happens on the failure paths you already handled.** You wrote `except FileNotFoundError: return "No failure log found at that path."` on Day 12. Does your docstring mention that? If a model can't predict that a missing file produces a clean message instead of an error, it can't reason about what to do next as confidently as it could if the docstring told it up front.

**Rule 4: One tool, one job.** `run_pytest_suite` runs tests; it doesn't also try to parse and summarize the results, format them for Slack, and email a teammate. A tool that does five things needs a description five times as precise to be used correctly, and still won't be, reliably. This is the same "single responsibility" instinct you already know from writing testable functions: it applies to tool boundaries for exactly the same reasons.

**Rule 5: Assume zero shared context, every time.** This is Day 12's self-check made into a standing rule rather than a one-off question: write every description as if the reader has never seen this codebase, this project, or this workbook. You know `test_path` defaults to `"tests/"` relative to wherever the server happens to run: does the description say so, or does it rely on you already knowing that from having written the code?

**Rule 6: Precise types beat permissive types.** A parameter typed as `str` when it's really always one of three known values gives the model far more room to send something malformed than a type that constrains the possibilities up front (an enum-like constraint, where your SDK version supports it, or at minimum a description that enumerates the valid values explicitly).

### 3. The stranger test, run for real

Day 12's self-check asked you to imagine handing your server to a teammate with zero context. Today, actually do it, as literally as you can manage:

1. Close the file. Don't look at `test_tools_server.py`'s implementation.
2. Read only the two docstrings, as they exist right now, exactly as a model calling `tools/list` would receive them.
3. For each one, write down: when would I call this, what would I pass, and what do I expect back, using only what the docstring told you.
4. Open the implementation and check your answers against what the code actually does. Any mismatch is a real schema defect, not a hypothetical one.

If you have a teammate, a study partner, or even just a version of yourself reading it fresh after a break, that's a better test than your own immediate judgment: you already know what the tool does, which makes it hard to notice what the docstring failed to say.

### 4. Diagram: Module 3's whole arc, in one picture

<img class="diagram" src="diagram_day14.png" alt="Days 10 through 14, as one continuous arc from theory to your own working client">
<p class="diagram-caption">Diagram: what each day of Module 3 actually added</p>

Walk it left to right, out loud, once, before moving on: Day 10 gave you the vocabulary and the reason the vocabulary exists (N×M, host/client/server, JSON-RPC). Day 11 proved that vocabulary describes something real by connecting to someone else's production-grade server. Day 12 flipped you from consumer to producer: you became the "someone else." Day 13 flipped the other role too: you replaced LM Studio's client-side machinery with your own code. Day 14 is where all four of those become something you can defend, not just something you did.

### 5. Your first real `decisions.md` entry

Every module so far has mentioned `decisions.md` as the place architectural choices get recorded, ADR-style. Today you have a real one to write, because Day 11 actually surfaced a live trade-off: stdio versus Streamable HTTP for `test_tools_server.py`. Use this shape:

```
## ADR-001: stdio transport for test_tools_server.py

**Status:** Accepted

**Context:**
test_tools_server.py needs a transport for MCP communication. The two
options available are stdio (subprocess, stdin/stdout) and Streamable
HTTP (network service, shared across clients). This project is a
single-developer capstone running entirely on one local machine, with
no requirement (yet) for multiple simultaneous users or remote access.

**Decision:**
Use stdio. The host (LM Studio, and later capstone_agent.py) launches
test_tools_server.py as a subprocess per session; no network port is
opened.

**Consequences:**
- No authentication or session management needed: the OS process
  boundary is the security boundary.
- The server cannot currently be shared across multiple machines or
  users without each one running its own subprocess.
- Revisiting this decision would matter if: the tool needs to run on
  shared infrastructure, or multiple team members need to hit one
  running instance simultaneously (see Day 11's stdio-vs-HTTP diagram).

**Alternatives considered:**
Streamable HTTP was considered and rejected for now: it solves a
multi-user/remote-access problem this project doesn't currently have,
at the cost of needing session handling and network exposure this
project doesn't currently need either.
```

Notice the shape of a good ADR entry: it names the alternative you didn't pick and says why, not just the one you did. "I used stdio" is a fact. "I considered HTTP and rejected it because this project doesn't have the multi-user requirement that would justify its added complexity" is a decision, and it's the version that survives an interviewer asking "why not HTTP?" without you having to improvise an answer on the spot.

## Practice

1. **Run the stranger test from Section 3 against both of your Day 12 tools**, exactly as described, and record any mismatches you find.

2. **Rewrite both docstrings against Section 2's six house rules.** Keep your "before" versions somewhere (a git diff is enough), the comparison is itself useful evidence for `docs/schema-design-notes.md`. Section 2's weak/strong table used a generic example; here's one reasonable rewrite of your actual two tools, to check your own attempt against rather than the only correct answer:

   **`run_pytest_suite`, before (Day 12):**
   ```python
   def run_pytest_suite(test_path: str = "tests/") -> str:
       """Run the pytest suite at the given path and return the raw output.

       Args:
           test_path: Relative path to the test directory or file.
       """
   ```

   **`run_pytest_suite`, after:**
   ```python
   def run_pytest_suite(test_path: str = "tests/") -> str:
       """Run the pytest suite at the given path and return its combined
       stdout and stderr, including full tracebacks for any failures.

       Use this to execute or re-run tests. Use get_last_failure_log
       instead if you only need to inspect a previous run's log without
       re-executing anything.

       Args:
           test_path: Path to the test directory or file, relative to
               the directory this server process was launched from.
               Defaults to "tests/". The run is terminated if it
               exceeds 120 seconds.
       """
   ```

   **`get_last_failure_log`, before (Day 12):**
   ```python
   def get_last_failure_log(log_path: str = "reports/last_run.log") -> str:
       """Return the contents of the most recent test failure log.

       Args:
           log_path: Relative path to the log file.
       """
   ```

   **`get_last_failure_log`, after:**
   ```python
   def get_last_failure_log(log_path: str = "reports/last_run.log") -> str:
       """Return the contents of the most recent test failure log,
       without re-running any tests.

       Use this to inspect a previous run's output. Use
       run_pytest_suite instead if you need current results. If no
       file exists at log_path, returns the message "No failure log
       found at that path" instead of raising an error.

       Args:
           log_path: Path to the log file, relative to the directory
               this server process was launched from. Defaults to
               "reports/last_run.log".
       """
   ```

   Checked against Section 2's rules: Rule 1 is why both now open with "Use this... use X instead if..." Rule 2 is why "relative to" now names what it's relative to, instead of leaving "relative" dangling. Rule 3 is why the missing-file message and the 120-second cutoff are now stated up front instead of living only in the code. Rule 5 is why "the directory this server process was launched from" is spelled out rather than assumed. Rule 6 is worth noting by its absence here: neither parameter has a natural restricted set of values the way a hypothetical `format: "json" | "text"` parameter would, so precise-vs-permissive typing doesn't force a change to these two specific tools: not every rule changes every docstring, and that's fine.

3. **Write the ADR from Section 5**, adapted to your actual project details rather than copied verbatim.

4. **Answer Module 3's full self-check set** (compiled below) from memory, in one sitting, without opening any previous day's file. Note which ones you couldn't answer cleanly: that's your real signal for what to review before moving on, not a grade.

## Common Pitfalls

- **Treating this as a proofreading pass instead of a design review.** Fixing typos in a docstring isn't the same exercise as checking whether it disambiguates this tool from its neighbors (Rule 1) or states its failure behavior (Rule 3). Read for content, not just wording.
- **Writing the ADR after the fact as pure justification.** The point of Section 5's format is capturing real reasoning, including the alternative you rejected and why: not constructing a plausible-sounding paragraph after you've already committed to stdio for unrelated reasons (it was simpler to set up). If that's the honest reason, say that; a genuine "I picked the simpler option because this project doesn't yet need the complexity" is a perfectly good, defensible ADR.
- **Skipping the self-check compilation because you feel confident.** The value is in the specific items you can't answer cleanly, which confidence alone won't reveal: actually attempt every one before checking against earlier days.
- **Applying the house rules only to new tools going forward.** Rules 1-6 apply retroactively to `read_file` and `run_shell` from Module 2 just as much as to Day 12's MCP tools: schema quality isn't a Module 3-specific concern, it just got higher stakes there.
- **Confusing "one tool, one job" (Rule 4) with "never add a second tool."** The rule is about a single tool's scope, not about keeping your total tool count low: `test_tools_server.py` having two focused tools is exactly right; one bloated tool trying to do both jobs would be worse, not more efficient.

## Why This Matters for Test Automation

Schema quality is one of the few pieces of this whole workbook that's almost entirely free to get right and expensive to get wrong later: a better docstring costs you two extra sentences today; a vague one costs you a confusing debugging session weeks from now when a model (or a teammate) misuses a tool it was never actually told how to use correctly. That asymmetry is worth being able to state plainly in an interview: "I treat tool descriptions as a correctness concern, not a documentation nice-to-have, because under MCP the docstring literally is the schema a model reasons from."

The ADR habit matters independently of MCP specifically. "Why did you choose X" is one of the most common interview questions in any senior engineering conversation, and "I have a written record of the alternative I considered and rejected, and why" is a categorically stronger answer than reconstructing your reasoning live under pressure.

## Module 3 Self-Check (full set, answer from memory)

**From Day 10:**

- What specifically does MCP solve that your Module 2 `DISPATCH` dict didn't?
- Does an MCP server necessarily require a network connection? Why or why not?
- What's the difference between a tool, a resource, and a prompt in MCP terms?

**From Day 11:**

- Why does stdio make sense for Playwright MCP on your laptop, but not for a tool your whole team needs to share?
- What does Playwright MCP actually read from a page to decide what's clickable, and why does that matter for reliability?

**From Day 12:**

- Walk through, from memory, the four things `@mcp.tool()` reads off your function to build its schema.
- Why does `run_pytest_suite` return combined stdout/stderr even when pytest fails, instead of raising an exception?

**From Day 13:**

- Walk through what happens on the wire between your script and the server subprocess, from `stdio_client()` to a returned `call_tool()` result.
- Why does a bare `print()` statement inside an MCP server break things?

**New today:**

- What's the difference between a schema that's merely accurate and one that would survive Section 3's stranger test?
- What does a good `decisions.md` entry include that a one-line "I used stdio" doesn't?

## Assignment

Produce two files:

1. `docs/schema-design-notes.md`: your six house rules (or your own refined version of them), the before/after diff of your Day 12 docstrings, and what the stranger test actually revealed when you ran it for real.
2. A new entry in `decisions.md`: the stdio-vs-HTTP ADR from Section 5, adapted to your project's real specifics.

## External Links

- MCP tool annotations and description guidance (official): https://modelcontextprotocol.io/specification/latest/server/tools
- Architecture Decision Records overview (the ADR format this workbook uses): https://github.com/joelparkerhenderson/architecture-decision-record
- Google's API design guidance on method naming and documentation (the same principles, outside MCP specifically): https://cloud.google.com/apis/design

**Module 3 complete.** You've gone from a diagram of what MCP solves (Day 10), to using a real server built by someone else (Day 11), to building and exposing your own (Day 12), to replacing the last piece of borrowed infrastructure (the client itself) with code you wrote and understand (Day 13), to a set of house rules and a documented decision you can defend under questioning (Day 14). Next: Module 4, Capstone & CV Polish. Every piece from Modules 1 through 3 now assembles into one project.
