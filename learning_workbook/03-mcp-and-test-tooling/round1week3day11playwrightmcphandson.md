<div class="day-label">Day 11</div>

# Module 3, Day 11: Playwright MCP, Hands-On

<div class="meta-line">~1.5-2 hrs | Difficulty: Beginner-Intermediate</div>

<div class="tldr-box">
<strong>TL;DR:</strong> Today the host/client/server diagram from Day 10 stops being a diagram and becomes three things actually running on your machine: LM Studio (host), its built-in MCP client, and Playwright MCP (server), a real, Microsoft-maintained browser automation tool you connect with a six-line config file and zero integration code. You'll drive a real browser through your local model, and understand exactly why it works without you writing a single line of browser-automation code yourself: Playwright MCP reads the page's accessibility tree instead of pixels, which is what makes it fast, deterministic, and LLM-friendly all at once.
</div>

## Objective

<div class="objective-box">
By the end of today you have Playwright MCP connected to LM Studio and have driven at least one real browser action through your local model, end to end, no shortcuts. You can explain precisely why <code>stdio</code> is the right transport choice for this setup and name the point at which it stops being the right choice. You can also explain, at a mechanical level, why Playwright MCP doesn't need a vision model to "see" a web page.
</div>

## Theory

### 1. What's about to happen on your machine, concretely

Day 10 was diagrams and JSON on a page. Today, when you edit `mcp.json` and ask your model to navigate to a website, here's the literal sequence of operating-system-level events that fires:

1. LM Studio reads `mcp.json`, sees a server named `playwright`, and launches `npx @playwright/mcp@latest` as a **child process** on your machine.
2. That child process starts talking JSON-RPC 2.0 over stdio: exactly the newline-delimited messages from Day 10, exactly the `initialize → tools/list` handshake.
3. LM Studio's built-in MCP client now has a live list of tools (`browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, and roughly thirty others) which it hands to your model as part of the `tools=[...]` schema, the same shape Module 2 taught you to expect.
4. When your model decides to call `browser_navigate`, LM Studio sends a `tools/call` request to that subprocess, which drives a real, invisible (headless, by default) Chromium instance to actually load the page.
5. The result (not a screenshot, a structured text snapshot) flows back through the same subprocess, back into your model's context, and your model reports back to you in plain language.

Nothing about this is new machinery. It's the exact host/client/server roles and the exact JSON-RPC lifecycle from Day 10, now with a real browser sitting at the end of the chain instead of a diagram.

### 2. Why stdio is the right default here, and precisely where that stops being true

Day 10 introduced stdio and HTTP as MCP's two transports. Today is where that choice has real consequences, not just definitional ones.

stdio's entire model is **one server subprocess per user, per host**. When you connect Playwright MCP through LM Studio, `npx @playwright/mcp@latest` launches as a process that belongs to you, on your machine, for your session: nobody else's traffic touches it, and it dies the moment LM Studio stops it. This is precisely why stdio needs no authentication, no network exposure, and no session management: the operating system's process boundary *is* the security boundary. For a single developer running a single local tool, that's not a limitation: it's the simplest correct answer available.

That same property is exactly what breaks the moment you try to share one server across a team. If ten engineers all wanted to hit "the same" Playwright MCP instance, stdio's model would require ten separate subprocesses (one per engineer, each spun up locally) because stdio has no concept of multiple simultaneous remote clients talking to one running process. That's not a bug to work around; it's a deliberate boundary. The moment you need one server instance to be reachable by many users at once (a shared team tool, a server running on infrastructure nobody's laptop hosts) you reach for **Streamable HTTP** instead, where the server is a genuine network service, requests carry a session id, and any number of clients can connect to the one running instance over HTTPS.

<div class="diagram-block">

![stdio: one subprocess per user, versus Streamable HTTP: one shared network service](diagrams/stdio_vs_http.png)

<div class="diagram-caption">Diagram: stdio's process-per-user model versus HTTP's one-shared-service model</div>
</div>

Neither transport is strictly "better": they answer different deployment questions. Today's setup (you, one laptop, one local tool) is exactly the case stdio was designed for, which is why Day 12's server and Day 13's client both use it too. Keep the HTTP side of this diagram in your back pocket, though: it's exactly the shape a `decisions.md` entry needs when you eventually justify staying on stdio for this capstone rather than reaching for HTTP "just in case."

### 3. How Playwright MCP actually "sees" a page: the accessibility tree, not pixels

This is worth understanding precisely, because it's the specific engineering choice that makes Playwright MCP fast and reliable enough for an LLM to drive turn after turn.

A naive way to let a model control a browser would be: take a screenshot, hand the image to a vision-capable model, ask it to guess pixel coordinates to click. That approach genuinely works, and Playwright MCP even supports it as an optional **vision mode** for edge cases (canvas elements, games, pages with broken semantic markup), but it's slow, token-heavy, and fundamentally probabilistic: the model is estimating where a button is, not being told where it is.

Playwright MCP's default mode instead reads the page's **accessibility tree**: the same structured, role-based representation of a page that screen readers use. Every interactive element gets a semantic description (its role, its accessible name, a stable reference id), and calling `browser_snapshot` returns that structure as text, not pixels:

```
- button "Sign in" [ref=e14]
- textbox "Email address" [ref=e15]
- textbox "Password" [ref=e16]
- link "Forgot password?" [ref=e17]
```

Your model then calls `browser_click` with `ref=e14`, and the click lands on exactly that button: deterministically, every time, regardless of where it happens to be positioned on screen, what font rendered it, or whether the page redesigned its CSS last week. This is why the docs describe the approach as "fast and lightweight" and "deterministic": there's no image to encode, no vision model to run, and no ambiguity about which element `ref=e14` refers to. It's the same reliability argument Day 1 made about quantization and tool-calling JSON, one level up the stack: precise, structured input produces precise, structured behavior; ambiguous input (raw pixels) produces ambiguous behavior (approximate clicks).

### 4. Anatomy of `mcp.json`

The config that wires this together is small on purpose:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

Each field maps directly onto Day 10's roles:

- `"playwright"`: a name *you* choose; it's how this server shows up in LM Studio's UI and in any logs.
- `"command"` and `"args"`: literally the subprocess launch line. LM Studio runs the equivalent of `npx @playwright/mcp@latest` in a terminal on your behalf; there's no magic beyond process spawning.
- Everything else (the JSON-RPC handshake, tool discovery, the stdio pipes) is handled for you by LM Studio's built-in MCP client: the exact `mcp.ClientSession`-shaped machinery you'll write yourself, by hand, on Day 13.

A couple of optional fields you'll see in other people's configs, worth recognizing even though today's minimal version doesn't need them: `"timeout"` (how long to wait for the subprocess to respond before giving up) and `"disabled"` (a way to keep a server registered but temporarily off, without deleting the config).

### 4.1 Verifying the connection independently: MCP Inspector

Day 2 taught you not to trust a claimed connection until you'd verified it yourself with `curl`, rather than trusting an app's UI at face value. Today's setup has no HTTP endpoint to `curl`, but MCP ships a direct equivalent: the official **MCP Inspector**, a tool that connects to any MCP server (stdio or HTTP) completely independently of LM Studio, and lets you browse its tools and call them by hand.

Run it directly against Playwright MCP, with no LM Studio involved at all:

```
npx @modelcontextprotocol/inspector npx @playwright/mcp@latest
```

The first run installs the Inspector itself: expect an `Ok to proceed?` prompt from `npx` the very first time, the same kind of first-run pause Section 4's config caused. It then prints a local URL (typically `http://localhost:6274`) with a session token already filled in. Open it, click **Connect**, then **List Tools**: you're now looking at the exact `tools/list` response from Day 10's JSON examples, rendered as a browsable UI instead of raw text. Pick `browser_navigate`, type in a URL argument by hand, and call it: you'll see the real `tools/call` request and response, entirely independent of whatever LM Studio's chat window is or isn't showing you.

<div class="callout-box">
This distinction is the whole point, the same way it was on Day 2: if something isn't working, the Inspector tells you whether the problem is the <em>server itself</em> (visible here, with LM Studio out of the picture entirely) or something specific to <em>LM Studio's integration</em> of it (only visible there). Without an independent tool, a broken connection and a broken server look identical from inside LM Studio's UI alone.
</div>

### 5. Where your own code will stand tomorrow

<div class="callout-box">
Today, LM Studio is doing two jobs at once: it's the <em>host</em> (embedding the model, owning the conversation) and it's silently running the <em>client</em> (the stdio connection to Playwright MCP) behind its UI, so you never see that machinery directly. Day 13 pulls the client-side code out of LM Studio's UI and puts it in your own hands, a standalone script holding an <code>mcp.ClientSession</code>, talking to a server you wrote yourself. Today's exercise is what that will feel like from the *outside*; Day 13 is the same interaction from the *inside*.
</div>

### 6. Diagram: the full request, start to finish

<div class="diagram-block">

![Request flow: your model, through LM Studio, through Playwright MCP, to a real browser and back](diagrams/request_flow.png)

<div class="diagram-caption">Diagram: one tool call's full round trip through today's stack</div>
</div>

## Practice

1. **Confirm Node.js is installed and current enough.** Playwright MCP requires a reasonably recent Node.js (18 or later). In PowerShell or Git Bash:
   ```
   node --version
   npx --version
   ```
   If either command isn't found, install Node.js from nodejs.org before continuing: everything below depends on `npx` being able to run.

2. **Open LM Studio's MCP configuration.** In the sidebar, find the **Program** tab, then **Install → Edit mcp.json** (exact wording may vary slightly by LM Studio version, if you can't find it, the search/discover icon's tooltip text is the fastest way to locate it).

3. **Paste the config from Section 4** into `mcp.json` and save. LM Studio should show `playwright` as a connected server: this is your visual confirmation that steps 1-2 of Day 10's lifecycle diagram (`initialize`, `tools/list`) already succeeded before you've typed a single prompt.

4. **Verify it independently with MCP Inspector before trusting LM Studio's UI alone.** Run `npx @modelcontextprotocol/inspector npx @playwright/mcp@latest` from Section 4.1, open the URL it prints, click **Connect**, then **List Tools**. Seeing the same tool list here, with LM Studio completely out of the picture, is stronger evidence the server itself works than any amount of chat-window activity.

5. **First run will be slower than every run after it.** The very first time this config loads, `npx` has to download the `@playwright/mcp` package itself, plus Chromium binaries the first time Playwright needs them: this can take a couple of minutes on a slow connection. Don't assume something's broken; check LM Studio's server/connection indicator (or the Inspector's own connection status) before troubleshooting further.

6. **Drive one real action.** In a chat with your model (tools enabled), ask: *"Navigate to example.com and tell me the page title."* Watch for your model calling `browser_navigate`, then something like `browser_snapshot` or a title-reading tool, before it answers you in plain language. If LM Studio shows tool-call activity in the chat, you're watching Day 10's `tools/call` JSON happen in real time, just rendered as a UI instead of raw JSON.

7. **Push it one step further.** Ask a second, slightly harder question in the same chat (e.g. *"Now find a link on that page and tell me where it goes"*) and watch whether your model correctly reuses the browser session rather than re-navigating from scratch. This previews Day 4's lesson about growing conversation history: each additional turn re-sends more context, and you're now watching that happen with real tool calls instead of synthetic weather-tool JSON.

## Common Pitfalls

- **Assuming the config file is JavaScript.** `mcp.json` is strict JSON: no trailing commas, no comments, double-quoted keys and strings only. A single stray comma is enough to make LM Studio silently fail to load the server.
- **Not waiting out the first, slow run.** The first `npx @playwright/mcp@latest` invocation downloads a package and possibly a Chromium binary: treat a long pause on the very first connection attempt as normal, not broken.
- **Confusing "no visible browser window" with "nothing is happening."** Playwright MCP runs headless (no visible window) by default. The absence of a browser window popping up on your screen is expected behavior, not a failure signal: trust the tool-call activity in LM Studio's chat instead.
- **Only ever verifying through LM Studio's chat window.** A chat window conflates three different things that could each independently be broken (the server, the connection, and your prompt's phrasing) into one "it didn't work" signal. MCP Inspector isolates the first two; without it, you're debugging blind.
- **Forgetting `@latest` pins nothing.** Using `@latest` in `args` means every fresh `npx` invocation can pull a newer version of the package: fine for exploration, but worth knowing if a behavior you rely on today changes unannounced next month. Pinning an exact version is the fix, and a good `decisions.md`-worthy trade-off (reproducibility vs. always having the newest tools).
- **Treating a vague natural-language instruction as a debugging step.** If your model doesn't call the tool you expect, don't immediately assume the MCP connection is broken: check whether your prompt gave it a clear enough reason to reach for a tool at all. This is Module 2's tool-description reliability lesson wearing a different hat: an underspecified *instruction* can look identical to an underspecified *tool schema* from the outside.
- **Mixing up which port belongs to what, out of old habit.** There's no port here at all: stdio doesn't use one. If you catch yourself looking for a `localhost:PORT` the way Day 2 taught you to for LM Studio's own API server, that instinct doesn't apply to this connection. (MCP Inspector's own web UI is the one exception: that port belongs to the Inspector, not to Playwright MCP.)

## Why This Matters for Test Automation

This is the clearest, fastest payoff Day 10's theory produces: you just connected a real, Microsoft-maintained, production-grade browser automation tool to your local model using a six-line config file and zero lines of Selenium- or Playwright-API code. That's the N×M problem collapsing in front of you, not an abstract claim from yesterday's reading. It's also a direct preview of your own capstone's shape: `test_tools_server.py` (Day 12) is architecturally identical to Playwright MCP from LM Studio's point of view: a stdio subprocess exposing tools over the same JSON-RPC lifecycle. The only difference is who wrote it.

The accessibility-tree design choice is worth carrying into interviews too, independent of MCP specifically: a QA engineer who can explain *why* structured, role-based page representations beat pixel-based automation for reliability (not just that Playwright happens to do it that way) is demonstrating the same "prefer structured, precise input over ambiguous input" instinct that shows up everywhere else in this workbook, from Day 1's quantization-vs-tool-calling argument to Module 2's schema-design lesson.

## Assignment

Add to `docs/setup-notes.md` (as an addendum to Day 2's entry):

1. Your working `mcp.json` contents (the real file, not a paraphrase).
2. A full transcript of your successful `example.com` interaction: the prompt you sent, and the model's final answer. If LM Studio shows the intermediate tool calls, include at least one (tool name + arguments) as evidence the connection actually worked end-to-end, not just that the model produced a plausible-sounding answer.
3. One or two sentences: did you hit the first-run slowdown from Practice step 5? How long did it take, and did LM Studio (or the Inspector) give you any indication anything was happening?
4. What MCP Inspector's tool list showed you, and whether it matched LM Studio's: your actual independent-verification evidence, not just a description of the exercise.
5. One sentence answering the Self-Check's first question below, written as if explaining it to a teammate who's never heard of MCP.

## Self-Check

- Why does `stdio` make sense for this setup, but not for a tool your whole team needs to share? Answer with the actual mechanism (process-per-user), not just "because stdio is local."
- What does Playwright MCP actually read from a page to decide what's clickable: pixels, or something else? Why does that choice matter for reliability?
- If your model calls `browser_navigate` and nothing visibly happens on your screen, is that necessarily a bug? Why or why not?
- What two roles is LM Studio playing simultaneously in today's setup, and which one does Day 13 move into your own code?
- What's the practical risk of leaving `@latest` in a tool's `args` indefinitely, versus pinning a specific version?
- What can MCP Inspector tell you that LM Studio's chat window alone cannot, and why does that distinction matter when something isn't working?

## External Links

- Playwright MCP (official repository and docs): <https://github.com/microsoft/playwright-mcp>
- Playwright's own MCP getting-started guide: <https://playwright.dev/docs/getting-started-mcp>
- MCP Inspector (official server debugging/testing tool): <https://github.com/modelcontextprotocol/inspector>
- MCP transports specification (stdio and Streamable HTTP, in full): <https://modelcontextprotocol.io/specification/latest>
- LM Studio's MCP documentation: <https://lmstudio.ai/docs/app/mcp>
- Node.js (required for `npx`): <https://nodejs.org>

---

**Next:** Day 12, Write Your Own MCP Server. You've now used someone else's server end-to-end; today you write one, using the same FastMCP SDK pattern, exposing two tools your capstone will call directly in Module 4.
