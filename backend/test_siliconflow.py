from openai import OpenAI

# 请替换成你自己的 API Key
YOUR_API_KEY = "sk-b96Q5iFRKzugfe8BfEAf6XhWU0pDGAXWZKDhwi1V5uPPOWJe"
client = OpenAI(
    api_key=YOUR_API_KEY,
    base_url="https://api.siliconflow.cn/v1"
)

# 调用大模型
response = client.chat.completions.create(
    # 选择一个合适的模型，比如这个 72B 的 Qwen
    model="Qwen/Qwen2.5-72B-Instruct",
    messages=[
        {"role": "user", "content": "你好，请用一句话简单介绍一下静态时序分析（STA）是什么。"}
    ],
    temperature=0.7,
    max_tokens=1024
)

print(response.choices[0].message.content)