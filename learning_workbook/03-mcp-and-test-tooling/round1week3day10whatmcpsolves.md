<div class="day-label">Day 10</div>

# Module 3, Day 10: What MCP Solves

<div class="meta-line">~1-1.5 hrs | Difficulty: Beginner-Intermediate</div>

<div class="tldr-box">
<strong>TL;DR:</strong> Before a shared protocol existed, every agent framework needed custom glue code for every tool it wanted to use: an N×M integration problem, the same disease Language Server Protocol (LSP) cured for editors and programming languages. MCP applies that fix to AI agents and tools: a <strong>host</strong> talks to any <strong>server</strong> through a standard <strong>client</strong> connection, over JSON-RPC 2.0, regardless of what the server does internally. Today is theory-only (no code) but it's the theory that makes the next four days (Playwright MCP, your own server, calling it from Python, schema design) click into place as applications of one idea instead of four separate tricks.
</div>

## Objective

<div class="objective-box">
By the end of today you can explain, from first principles, why MCP exists as a <em>protocol</em> rather than a library or a framework feature; you can correctly assign host/client/server labels to any AI tool-using setup, including your own Module 4 capstone, which you haven't built yet; and you can describe the <code>initialize → tools/list → tools/call</code> message lifecycle, including what capability negotiation actually communicates, precisely enough to debug a broken connection later without guessing. You can also name MCP's three primitives (tools, resources, prompts) and explain why this workbook's agent loop only ever needs the first one.
</div>

## Theory

### 1. The problem MCP was built to solve: N×M integration

Your Module 2 `DISPATCH` dict works. It's real, tested, and it runs `read_file` and `run_shell` end-to-end against your local model. But look closely at where that capability actually lives: inside one Python file, wired to one specific agent loop, callable only by code that imports that exact file. Nothing else in your setup (not LM Studio's chat window, not a teammate's CrewAI project, not a second script you write next month) can use your `run_shell` tool without you copying the function and its allowlist into that new context by hand.

Multiply that by a realistic number of tools and consumers and the shape of the problem becomes obvious:

| | 3 tools | 8 tools | 15 tools |
|---|---|---|---|
| 1 consumer (today) | 3 integrations | 8 integrations | 15 integrations |
| 3 consumers (you + LM Studio + a teammate) | 9 integrations | 24 integrations | 45 integrations |

Every cell in that table is hand-written, hand-maintained code that can silently drift out of sync with every other cell. The `run_shell` allowlist in your Module 2 script and the "same" tool re-implemented for a teammate's project are not guaranteed to agree on which commands are safe; and nothing forces them to. This is the **N×M integration problem**: N consumers, each needing custom code for M tools, means N×M separately-maintained pieces of glue.

This is not a new problem, and it's not unique to AI. The closest well-known precedent is **Language Server Protocol (LSP)**, which Microsoft introduced to solve the identical shape of problem for code editors. Before LSP, every editor (VS Code, Vim, Emacs, Sublime...) that wanted autocomplete, go-to-definition, and linting for every language (Python, Go, Rust, TypeScript...) needed its own bespoke integration per language. M editors × N languages meant M×N integrations, each maintained by a different team, each capable of behaving slightly differently. LSP's fix: every editor implements **one** client that speaks the protocol; every language tooling maintainer implements **one** server that speaks the same protocol. The integration cost drops from M×N to M+N; and, critically, an editor that didn't exist yet when a language server was written can still use it, for free, the day it implements the client side.

A second, more physical way to feel the same idea, if JSON-RPC and language tooling still feel abstract: think about peripherals before USB. A printer needed a printer cable, a scanner needed a scanner cable, and a camera needed its own proprietary connector: every device manufacturer solving "how do I talk to a computer" from scratch, per device, per computer. USB (and now USB-C) collapsed that by standardizing the physical and electrical interface exactly once: any compliant device plugs into any compliant port, and neither side needs to know anything special about the other beyond "we both speak USB." MCP is doing the software equivalent for agents and tools: the protocol is the standardized port, and it doesn't care which model is asking or what the tool does behind it, as long as both sides speak MCP.

MCP is that exact fix, applied to agents and tools instead of editors-and-languages, or cables-and-devices. Your `DISPATCH` dict is the pre-LSP, pre-USB world in miniature: correct, working, and non-transferable.

### 2. What MCP actually is, structurally: host, client, server

MCP defines three roles, precisely enough that "which one is this?" should always have a single correct answer once you know what a piece of software is actually doing.

| Role | What it is | What it owns | Examples in this workbook |
|---|---|---|---|
| **Host** | The user-facing application that embeds an LLM and needs tools | The conversation, the decision of when to call the model, which servers are available this session | LM Studio (Day 11), Claude Desktop, your own `capstone_agent.py` (Day 16) |
| **Client** | The connector object *inside* the host, maintaining one stateful connection to exactly one server | The protocol handshake, message framing, matching each response back to the request that triggered it | The `mcp.ClientSession` object you'll instantiate in Day 13's code |
| **Server** | The standalone process exposing tools/resources/prompts | The actual tool implementations; knows nothing about which host is connected or which LLM is being used | Playwright MCP (Day 11, someone else's code), `test_tools_server.py` (Day 12, yours) |

A few things about this table are easy to misread on first pass, so read them twice:

- **The host is not the client.** LM Studio, as an application, is the host. The specific connection LM Studio opens to Playwright MCP is a client, one of potentially several clients the host is running at once. If LM Studio is also connected to your `test_tools_server.py` in the same session, that's a *second* client, independent of the first. This distinction matters the first time you read an error message that says "client disconnected": that's telling you about one connection, not the whole application crashing.
- **A server knows nothing about your model.** Playwright MCP has no idea whether it's being driven by Qwen2.5-Coder-7B-Instruct on your CPU, GPT-4 in the cloud, or a human typing commands through a debugging tool. It only ever sees JSON-RPC requests and returns JSON-RPC responses. This is precisely what makes it reusable: the server's implementation is completely decoupled from whatever intelligence is deciding to call it.
- **One client is a 1:1 relationship with one server.** A host that wants to use three servers runs three clients, not one client juggling three connections. This is a deliberate isolation boundary, not an implementation detail: Module 3.7's schema-design lesson later in the week and Module 4's security thinking both lean on this isolation.

### 2.1 Mapping this onto your own capstone, before you've built it

This is the part worth sitting with, because it previews Days 11 through 16 as one continuous idea rather than four disconnected exercises:

<div class="callout-box">
<strong>Your setup this week:</strong> On Day 11, the <em>host</em> is LM Studio: you're driving Playwright MCP through LM Studio's chat window, and LM Studio owns the client connection for you behind its UI. On Day 12 you write <code>test_tools_server.py</code>, a <em>server</em>, and nothing else; a server has no idea who's going to connect to it. On Day 13 you write your <em>own</em> client code, a standalone Python script holding an <code>mcp.ClientSession</code>, replacing LM Studio's UI with code you control. By Day 16, your own <code>capstone_agent.py</code> has become the <em>host</em>: it embeds the model, owns the conversation, and manages one or more client connections to the servers you built in Module 3. Same three roles, the whole way through, only which piece of software is playing which role changes.
</div>

### 2.2 The three things a server can expose: tools, resources, and prompts

Everything so far has talked about "tools" as if that's all a server has to offer, because tools are the primitive Module 2's agent loop already knows how to use. MCP actually defines three distinct primitives a server can expose. Knowing all three now means you won't be thrown off later when the SDK or the spec mentions "resources" or "prompts" and you wonder if you missed a lesson.

| Primitive | Who decides to use it | What it actually is | Example |
|---|---|---|---|
| **Tools** | The model: it reads the descriptions and decides, mid-reasoning, whether to call one | A function the model can invoke with arguments; the result re-enters the conversation | `run_pytest_suite`, `get_last_failure_log` (Day 12) |
| **Resources** | The application or the user: attached deliberately, not chosen autonomously by the model | Read-only-ish content addressed by a URI (a file, a database row, a log) pulled into context on demand | A specific failure-log file a user picks from a file browser in the host's UI |
| **Prompts** | The user: selected explicitly, like a slash command | A reusable, parameterized prompt template the server ships, so a host can offer "run this exact workflow" as a one-click action | A hypothetical `/diagnose-latest-failure` template that pre-fills the exact prompt your Day 16 capstone would otherwise type out by hand |

The distinction that matters most for this workbook: **tools are model-controlled**, which is exactly why they're the primitive that plugs directly into Module 2's ReAct loop. The model reasons, decides to call one, and the result feeds back in, with no separate human decision inside that loop. Resources and prompts are **host- or user-controlled** instead: a person, or the host acting on the person's behalf, decides when to pull a resource into context or fire a prompt template, rather than the model reaching for it mid-reasoning. That's not a lesser use case, just a different one, and it's precisely why `test_tools_server.py` (Day 12) only ever exposes tools: tools are the one primitive whose control model matches the agent loop you already built. Know the other two exist (you're likely to meet them for real if you go deeper into MCP in Round 2) but nothing in this workbook asks you to implement them.

### 3. What actually crosses the wire: JSON-RPC 2.0

Every MCP message (in every direction, over every transport) is a **JSON-RPC 2.0** object. This is the same principle Day 3 established for the OpenAI-compatible API: once you know the message *shape*, the specific tool or server behind it stops being mysterious. JSON-RPC defines exactly two message shapes:

**A request**: client asks the server to do something:
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "method": "tools/call",
  "params": {
    "name": "run_pytest_suite",
    "arguments": { "test_path": "tests/" }
  }
}
```

**A response**: server answers, echoing the same `id` so the client can match it to the request that caused it:
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {
    "content": [
      { "type": "text", "text": "5 passed, 1 failed in 2.31s" }
    ],
    "isError": false
  }
}
```

Or, if something went wrong, an `error` field instead of `result`:
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "error": { "code": -32602, "message": "Unknown tool: run_pytest_suite" }
}
```

Notice this is structurally the same idea as the `tool_calls` JSON you already met in Module 2 and Day 3's streaming deltas: a function name plus a JSON blob of arguments, and a result that comes back keyed to the call that produced it. MCP doesn't invent a new concept here; it takes a convention every agent framework was already reinventing slightly differently, and pins it to one existing, boring, well-specified wire format (JSON-RPC 2.0 predates MCP by two decades) so no one has to agree on yet another custom shape.

There's a third message type worth knowing exists even though you won't use it much yet: a **notification**, a request with no `id` field, meaning the sender doesn't want or expect a response at all. MCP uses these for things like "the tool list just changed" announcements. The practical implication: if a message has no `id`, don't sit there waiting for a reply: there isn't going to be one.

### 4. The full lifecycle: initialize → tools/list → tools/call

A client doesn't just fire off `tools/call` the moment it connects: there's a fixed handshake first, so both sides agree on what the other supports before anything real happens:

```
HOST launches SERVER as a subprocess (stdio)
        │
        ▼
CLIENT ──── initialize ────────────────▶ SERVER
       (protocol version, capabilities)
        │
        ◀──── initialize response ──────┤
       (server's capabilities, name, version)
        │
CLIENT ──── notifications/initialized ─▶ SERVER
       (no response expected: a notification)
        │
        ▼
CLIENT ──── tools/list ─────────────────▶ SERVER
        │
        ◀──── tool schemas ──────────────┤
       (name, description, input schema, per tool)
        │
        ▼
   [ zero or more tools/call round-trips, ]
   [ each with its own id, for as long   ]
   [ as the session stays open           ]
        │
        ▼
CLIENT closes the connection; HOST may terminate the SERVER subprocess
```

Two details in this sequence connect directly to code you'll write later this week:

- The `tools/list` response is exactly what Module 4's `diagnose_failure()` function (previewed in `04-capstone-and-cv.md`) converts into the OpenAI `tools=[...]` schema at runtime: `t.inputSchema` becomes `parameters` for each tool. The model never talks to MCP directly; your code translates MCP's tool schemas into the tool-calling format your local model already understands from Module 2.
- `tools/call`'s `id` field is what lets a client correctly match an eventual response to the request that triggered it, even if (in principle) multiple calls were in flight, the same matching problem Day 3's streaming `tool_calls` deltas solved differently, by relying on chunk ordering instead of an explicit id.

### 4.1 What's actually inside the handshake: capability negotiation

The `initialize` request and response in the diagram above aren't just a formality: they're where the client and server tell each other, precisely, what they each support, before either side assumes anything. An illustrative exchange looks like this:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "<date-versioned string, e.g. 2025-06-18>",
    "capabilities": {},
    "clientInfo": { "name": "capstone-agent", "version": "0.1.0" }
  }
}
```

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "<date-versioned string, negotiated with the client's>",
    "capabilities": {
      "tools": { "listChanged": true }
    },
    "serverInfo": { "name": "test-tools-server", "version": "0.1.0" }
  }
}
```

(The exact `protocolVersion` string is whatever your installed SDK reports: treat it the way Day 2 taught you to treat a model's id string: check it yourself, don't assume it from a tutorial.)

Two things about that `capabilities` object are worth sitting with. First, it's additive and optional: a server that only implements tools simply omits `resources` and `prompts` from its `capabilities` entirely, and a well-behaved client is expected to handle that gracefully rather than assume every server offers everything. Second, this is the first place in the whole protocol where a security-relevant idea shows up: a server *declares* what it can do, and the host is the one that decides what to actually allow or surface to the user: a host is never obligated to grant a server everything it claims to support. That "server declares, host decides" split is a thread you'll pick back up directly in Module 4, when `architecture.md`'s Security Model section asks you to write down exactly what your own MCP server can and can't touch.

### 5. Transports, briefly (Day 11 goes deeper)

MCP separates *what a message says* (JSON-RPC 2.0, covered above) from *how it physically travels* (the transport). Two transports matter for this workbook:

- **stdio**: the server runs as a local subprocess; messages travel over the subprocess's stdin/stdout. No network socket, no port, no firewall consideration at all. This is the default for local dev tools, and it's what Playwright MCP and your own `test_tools_server.py` both use.
- **HTTP / streamable-HTTP**: for remote or shared servers, e.g. one MCP server running as a persistent service that an entire team connects to over a network.

<div class="callout-box">
<strong>Worth flagging now, before it becomes a confusing surprise later:</strong> the word "server" strongly suggests networking, but a stdio MCP server never opens a network port at all: it's a subprocess your host starts and talks to over stdin/stdout, the exact same mechanism you'd use to pipe data between two command-line programs. "Server" here means "the side of the connection that serves tools," not "a thing with an IP address." Day 11 and Day 12 both use stdio exclusively.
</div>

### 6. What MCP does *not* change

This is the single most important framing for how you'll describe your own capstone in an interview, so it deserves its own numbered section rather than a footnote.

Your Module 2 agent loop (reason, call a tool, execute it, feed the result back, repeat until a final answer) does not change shape at all once MCP enters the picture. Look again at `04-capstone-and-cv.md`'s `diagnose_failure()` function: it's the *exact same five-step loop* from Module 2's `run_agent()`. The only line of code that's different is where "execute" gets its tool definitions and its actual execution from: a local `DISPATCH[fn_name](**args)` call becomes `await session.call_tool(call.function.name, args)`. Everything upstream of that (the reasoning, the message history, the `max_iterations` safety guard, the pattern of feeding errors back as tool results instead of raising them) is identical.

This is worth being able to say plainly, because it's exactly the kind of distinction that separates "I used MCP" from "I understand what MCP is for" in an interview:

> "MCP didn't change my agent's reasoning loop at all: it changed where the loop's tools come from. That's the whole point: the loop shape is a separate concern from the tool source, and MCP only touches the second one."

### 7. Diagram: the N×M problem, before and after

<div class="diagram-block">

![Before MCP: every host integrates every tool directly](diagrams/before_only.png)

![After MCP: hosts and servers meet through one shared protocol](diagrams/after_only.png)

<div class="diagram-caption">Diagram: collapsing N×M integrations into M+N via one shared protocol</div>
</div>

The left diagram is today, in miniature: three different consumers of tools, each wired directly and separately to each tool they need, with no shared code path between them. The right diagram is the same three consumers and the same three tools, but every connection now passes through one standard protocol. Nothing about *what* the tools do changed: what changed is that adding a fourth consumer no longer means writing three more bespoke integrations; it means implementing the client side of MCP once, and every existing server is immediately usable.

### 8. Diagram: host / client / server, mapped to your own setup

<div class="diagram-block">

![Host, client, and server roles mapped onto this week's concrete setup](diagrams/roles.png)

<div class="diagram-caption">Diagram: one host, two independent client connections, two independent servers</div>
</div>

Notice the host in this diagram runs *two* clients, and each client talks to exactly *one* server, never the reverse. This is the concrete shape your own machine will have by the end of Day 11: LM Studio (host) connected simultaneously to Playwright MCP and, later, to your own server, through two separate, isolated client connections that don't know about each other.

## Practice

1. **Annotate the JSON pair.** Look back at the `tools/call` request and response in Section 3. Circle (on paper or in a text editor, doesn't matter) the two places the value `7` appears, and write one sentence explaining what would go wrong if the response echoed back a different `id` than the request sent.
2. **Diagram your own capstone, twice.** Using the roles table from Section 2, draw (boxes and arrows, plain text is fine) the host/client/server layout for two different points in this workbook: (a) Day 11, where LM Studio is the host, and (b) Day 16, where your own `capstone_agent.py` is the host. Label what's identical between the two drawings and what's different. If you'd rather not hand-draw it, describing it precisely in prose is an acceptable substitute: the goal is correctly assigning the three labels, not the medium.
3. **Audit your Module 2 `DISPATCH` dict against the N×M table.** For each tool you built (`read_file`, `run_shell`, and anything else you added), write one line: would this tool be worth promoting to a real MCP server given more than one consumer, or is it genuinely fine staying local forever? `run_shell`'s allowlist is the interesting case: think about what happens the day two different projects need "the same" allowlist and someone updates only one of them.

## Common Pitfalls

- **Thinking MCP replaces the agent loop.** It replaces *tool wiring*, not reasoning. Section 6 above exists specifically because this is the single most common conceptual mix-up going into Module 3.
- **Calling the whole application "the client."** Precisely, the client is the connector object living inside the host, not the application itself. LM Studio is a host that happens to run one or more clients internally.
- **Assuming a server always needs a network address.** stdio servers are local subprocesses with zero networking, see Section 5's callout. This misconception causes real confusion the first time someone looks for a port number that doesn't exist.
- **Treating the `id` field as optional busywork.** It's the only mechanism a client has for matching an eventual response to the request that produced it, essential the moment more than one call could be in flight, and a genuine debugging aid even when calls are strictly sequential.
- **Assuming MCP fixes vague tool descriptions.** The protocol transports your tool's `description` faithfully to whoever connects: it does not improve a bad one. This is the same reliability-lever lesson from Module 2.2, and it gets *higher* stakes under MCP, not lower, because strangers now reuse your schema without your mental model of the tool (Day 14 goes deep on this).
- **Confusing a request with a notification.** A message with no `id` is a notification: no response is coming, and waiting on one will hang your code for no reason.
- **Assuming one client can talk to multiple servers.** It's the reverse: each client is a dedicated 1:1 connection to exactly one server. A host using three servers is running three independent clients, not one client with three targets.
- **Treating resources and prompts as just "other tools."** They're separate primitives with separate control models: tools are model-controlled, resources and prompts are host- or user-controlled. `test_tools_server.py` exposing only tools is a deliberate scope choice matched to your agent loop's shape, not an oversight.
- **Assuming every server supports every primitive.** A server's `capabilities` object in the `initialize` response is additive and optional: check what a server actually declares before assuming it offers resources or prompts just because the SDK makes them available to implement.

## Why This Matters for Test Automation

The concrete payoff of today's theory shows up almost immediately: Day 11 has you driving Playwright MCP (a real, Microsoft-maintained browser automation tool) through your local model with zero integration code, purely because both sides speak MCP. That's the N×M problem collapsing in front of you, not an abstract claim. And it runs the other direction too: the `test_tools_server.py` you write on Day 12 becomes something a teammate, a different agent framework, or even Claude Desktop could connect to without touching your code, the moment it exists as a real MCP server instead of a dict living inside one script.

This is also a genuinely reliable interview differentiator, and worth rehearsing out loud once. A candidate who says "I called a function to run the tests" and a candidate who says "I exposed test execution as an MCP server specifically so any host (not just my own agent script) could reuse it without custom integration code" are describing the same underlying capability, but only the second answer signals systems-level thinking about integration cost across a team, not just a working demo.

## Assignment

Produce `docs/mcp-fundamentals.md` containing:

1. In your own words (3-5 sentences): the N×M integration problem, and how MCP collapses it into M+N. Feel free to lean on the LSP analogy if it helps it stick.
2. A table mapping host / client / server to two concrete setups: (a) LM Studio + Playwright MCP from Day 11, and (b) your own eventual capstone from Day 16.
3. The `initialize → tools/list → tools/call` lifecycle, either as a diagram or in your own words: precise enough that future-you could debug a stalled connection by checking which step it stopped at.
4. One paragraph: what MCP does *not* change about your Module 2 agent loop, and why that distinction is worth stating plainly in an interview rather than glossing over.
5. One or two sentences naming MCP's other two primitives (resources and prompts) and explaining why `test_tools_server.py` only needs to expose tools for what this workbook is building.

This file is also a good first candidate for a `decisions.md` entry once you actually pick stdio over HTTP for your own server on Day 12: today just sets up the vocabulary you'll need to write that entry precisely.

## Self-Check

- What specifically does MCP solve that your Module 2 `DISPATCH` dict didn't?
- In the host/client/server model, where does your own code sit on Day 11, and where does it move to by Day 16?
- Does an MCP server necessarily require a network connection? Why or why not?
- What wire-level protocol are all MCP messages formatted in, and what are the two required fields that let a response find its way back to the request that caused it?
- If your Module 2 reasoning loop barely changes once you adopt MCP in Module 4, what exactly *is* different?
- Why does a 1:1 client-to-server relationship matter, rather than one client juggling several servers at once?
- What's the difference between a tool, a resource, and a prompt in MCP terms, and which one does your Module 2 agent loop actually use?
- What does a server's `capabilities` object in the `initialize` response communicate, and why does "server declares, host decides" matter once you're thinking about security?

## External Links

- MCP official site and docs: <https://modelcontextprotocol.io>
- MCP specification (architecture, JSON-RPC message shapes): <https://modelcontextprotocol.io/specification/latest>
- Anthropic's original MCP announcement (design rationale): <https://www.anthropic.com/news/model-context-protocol>
- JSON-RPC 2.0 specification (the wire format MCP is built on): <https://www.jsonrpc.org/specification>
- Language Server Protocol overview (the pre-existing analogy MCP's own design borrows from): <https://microsoft.github.io/language-server-protocol/>
- Python MCP SDK: <https://github.com/modelcontextprotocol/python-sdk>

---

**Next:** Day 11, Playwright MCP, Hands-On. You'll drive a real browser through a real MCP server today's theory just explained, and see the host/client/server roles stop being a diagram and start being three things actually running on your machine at once.
