from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",  # 1234/v1 for LM Studio; use :11434/v1 for Ollama
    api_key="not-needed"  # local servers typically ignore this
)

response = client.chat.completions.create(
    model="qwen2.5-coder-7b-instruct",
    messages=[
        {
            "role": "user",
            "content": "A test suite has 40 tests, 8 failed, then 3 of those were fixed and re-run "
                       "successfully. How many tests are now passing?"
        }],
    temperature=0.2,
)

print(response.choices[0].message.content)
