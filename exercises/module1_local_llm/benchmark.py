from ai_lab.llm.client import run_non_streaming, run_streaming

PROMPTS = [
    "Explain the difference between a list and a tuple in Python.",
    "Write a function that reverses a string without using slicing.",
    "What does the SOLID acronym stand for in software design?",
    "Summarize what a race condition is, in three sentences.",
    "Convert this pseudocode to Python: for i from 1 to 10, print i squared.",
]


def benchmark(model: str, prompts=PROMPTS, runs: int = 3):
    results = []
    for prompt in prompts:
        for _ in range(runs):
            non_stream_elapsed, _ = run_non_streaming(prompt, model=model)
            ttft, stream_total, output = run_streaming(prompt, model=model)

            approx_tokens = len(output.split()) # rough proxy
            decode_time = stream_total - ttft if ttft else None

            results.append({
                "prompt": prompt[:40],
                "non_stream_sec": round(non_stream_elapsed, 2),
                "ttft_sec": round(ttft, 3) if ttft else None,
                "streaming_total_sec": round(stream_total, 2),
                "streaming_overhead_sec": round(stream_total - non_stream_elapsed, 3),
                "approx_tokens": approx_tokens,
                "approx_tokens_per_sec": round(approx_tokens / decode_time, 2)
                    if decode_time and decode_time > 0 else None,
            })
    return results


MODELS = {
"7b": "qwen2.5-coder-7b-instruct",
"4b": "google/gemma-4-e4b",
}

for label, model_id in MODELS.items():
    print(f"Benchmarking {label}: {model_id}")
    results = benchmark(model=model_id)
    print(results)
    # save results per label, e.g. to benchmark_results_{label}.json