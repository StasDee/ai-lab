# Module 1, Day 1: What "Local" Means, and Quantization
### ~1-1.5 hrs

## Objective

By the end of today you can explain, in your own words, what actually changes
when inference moves from a hosted API to your own machine, and calculate a
rough memory budget for any model you're considering, before downloading
anything.

---

## Theory

### What a hosted API is hiding from you

When you call `api.openai.com`, you send text and get text back. Everything
in between (which physical GPU your request landed on, how many other
requests are batched alongside yours, how the weights are sharded across
devices) is invisible and none of your concern.

Running locally removes that abstraction. Concretely, three things now live
on your machine instead of someone else's cluster:

- **Weights**: the model's learned parameters, as a file on disk (`.gguf`
  for the runtimes you'll use this module; `.safetensors` for the
  training/full-precision form you *won't* be using directly).
- **The inference engine**: the program that loads those weights into
  memory and executes the matrix multiplications, using your CPU's vector
  instruction set (AVX2/AVX-512 on x86, NEON on ARM/Apple Silicon).
- **The memory budget**: your RAM has to hold the weights, the KV cache
  (the running memory of the current conversation, this grows as context
  length grows), and everything else your OS and other apps need.

That third point is the one that will shape every model choice you make in
this workbook: **you now own the compute and memory budget.** A hosted
provider can throw a rack of GPUs at a request; you have one machine, and it
has to fit.

### GGUF: the file format built for this

GGUF (used by llama.cpp and, under the hood, by both LM Studio and Ollama)
bundles three things into one file:

1. The quantized weight tensors
2. The tokenizer
3. Metadata (architecture, context length, chat template, etc.)

Compare this to `.safetensors`, which is the format models are usually
*trained and published* in (full 16-bit or 32-bit precision): that format
assumes you have serious GPU memory to spare. GGUF exists specifically for
consumer CPU/Apple Silicon inference, and quantization is the mechanism that
makes that possible.

### What quantization actually does

Every weight in a neural network is a number. In full precision, that number
is stored as 16 or 32 bits. Quantization reduces that to as few as 2-8 bits
per weight, by grouping weights into blocks and storing each block as a
smaller set of discrete levels plus a scaling factor (this is why you'll see
names like `Q4_K_M`, "4-bit, K-quant variant, Medium", the K-quant schemes
selectively keep certain more-sensitive tensors at slightly higher precision
within an otherwise low-bit model).

The trade-off is simple to state and easy to underestimate in practice:
**fewer bits = less memory + faster inference, but a growing gap from the
original model's behavior.**

| Quant | Bits/weight (approx.) | Quality | Speed / memory | Use for |
|---|---|---|---|---|
| Q8_0 | ~8 | Near-original | Slower, more RAM | Quality-critical work, memory not a constraint |
| Q5_K_M | ~5 | Very close to Q8 | Balanced | Good middle ground |
| Q4_K_M | ~4 | Small, usually-acceptable dip | Fast, RAM-efficient | **Default starting point for this workbook** |
| Q2/Q3 | ~2-3 | Noticeable degradation | Fastest, least RAM | Avoid for agents (see below) |

### Why this matters *more* for agents than for chat

This is the single most important idea in today's material, so it's worth
sitting with: **plain chat degrades gracefully under quantization; tool
calling does not.**

If a heavily quantized model gets a little fuzzy in a chat response, you get
slightly-off prose, still readable, still useful. But an agent has to
produce *exact* structured output on every turn: the correct function name,
character-for-character, with arguments in valid JSON matching an exact
schema. There's no "close enough": a malformed call either doesn't parse or
calls the wrong tool. Aggressive quantization increases exactly this kind of
failure, because the model's precision loss shows up as small perturbations
in exactly the tokens where precision matters most.

**Practical floor for this workbook: Q4_K_M.** Below that, expect tool-call
reliability to degrade: you'll feel this directly once you build the agent
loop in Module 2, so it's worth internalizing now rather than discovering it
as a confusing bug later.

---

## Practice

No installation yet: that's tomorrow. Today's practice is entirely about
building the intuition for memory budgeting, so that when you *do* install
something tomorrow, you already know what should fit.

**Rough sizing formula** (good enough for planning, not exact):

```
size_in_GB ≈ (parameter_count × bits_per_weight) / 8 / 1,000,000,000
```

Add roughly 10-20% on top for metadata, tokenizer, and quantization
overhead. This is an estimate for planning purposes: actual file sizes vary
by quantization tool and model architecture, so always check the real
file size before committing to a download.

Work through this by hand for two candidate models at Q4 (~4 bits/weight):

- A 7B parameter model
- A 3B parameter model

Then do the same for the 7B model at Q8 (~8 bits/weight), so you can see the
difference precision makes concretely, not just as a table row.

---

## Assignment

Produce `docs/model-budget.md` with:

1. A table with your calculated approximate sizes for: 7B @ Q4, 7B @ Q8, 3B @ Q4
2. For each, a one-line note on how much headroom that leaves in a 64GB
   budget once you account for the OS, your IDE, and a growing KV cache
   during a multi-turn agent session
3. A one-paragraph recommendation: which combination (model size + quant)
   you're planning to load tomorrow, and why

This isn't throwaway practice: you'll compare this estimate against the
*actual* downloaded file size tomorrow, which is a useful reality check on
how good your mental model is.

---

## Self-Check

- Why does aggressive quantization (Q2/Q3) hurt tool-calling more than plain chat?
- What three things does a GGUF file bundle together, and why does that matter for portability?
- If your calculated budget for 7B @ Q4 left very little headroom in 64GB, what are your two options?

**Next:** Day 2, actually installing and running one of these models.
