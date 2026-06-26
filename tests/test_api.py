import sys
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from openai import OpenAI
import config

print(f"Base URL: {config.OPENAI_BASE_URL}")
print(f"Model: {config.OPENAI_MODEL}")

client = OpenAI(
    api_key=config.OPENAI_API_KEY,
    base_url=config.OPENAI_BASE_URL,
)

try:
    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        max_tokens=100,
        messages=[
            {"role": "system", "content": "你是一个 helpful 助手"},
            {"role": "user", "content": "你好，请介绍一下自己"},
        ],
    )
    print(f"Success!")
    print(f"Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
