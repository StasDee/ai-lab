import json
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="not-needed",
)

TOOL_SYSTEM_PROMPT = """You have access to one tool:
    get_weather(city: str) -> returns current weather for a city.
    When the user asks about weather, respond ONLY with JSON in this exact shape:
    {"tool": "get_weather", "arguments": {"city": "<city name>"}}
    Do not include any other text."""

def tool_call_validity_run(model: str, turns: int = 10):
    history = [{"role": "system", "content": TOOL_SYSTEM_PROMPT}]
    results = []
    cities = ["Paris", "Tokyo", "Nairobi", "Lima", "Oslo", "Cairo",
              "Manila", "Denver", "Perth", "Warsaw"]

    for i in range(turns):
        user_msg = f"What's the weather like in {cities[i % len(cities)]} right now?"
        history.append({"role": "user", "content": user_msg})
        response = client.chat.completions.create(
            model=model,
            messages=history,
            temperature=0.2,
        )
        reply = response.choices[0].message.content
        print(f"reply: {reply[:80]}")
        history.append({"role": "assistant", "content": reply})
        try:
            parsed = json.loads(reply)
            valid = isinstance(parsed, dict) and parsed.get("tool") == "get_weather"
        except json.JSONDecodeError:
            valid = False

        results.append({"turn": i + 1, "valid_json": valid, "raw_reply": reply[:80]})

    return results

model = "qwen2.5-coder-7b-instruct"
tool_call_validity_run(model)