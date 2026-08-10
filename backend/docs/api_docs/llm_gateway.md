# LLM Gateway

本模块封装 OpenAI-compatible 大模型调用，适配 SiliconFlow、vLLM 等兼容 `/v1/chat/completions` 的供应商。

## 环境变量

```env
LLM_PROVIDER=siliconflow
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_API_KEY=<your-api-key>
LLM_MODEL=deepseek-ai/DeepSeek-V4-Pro
LLM_TIMEOUT_SECONDS=60
```

## Python 模块调用

```python
import asyncio

from app.llm import (
    ChatGenerationOptions,
    OpenAICompatibleChatClient,
    OpenAICompatibleProvider,
    build_messages,
)


async def main():
    provider = OpenAICompatibleProvider(
        name="siliconflow",
        base_url="https://api.siliconflow.cn/v1",
        api_key="YOUR_API_KEY",
        model="deepseek-ai/DeepSeek-V4-Pro",
    )
    client = OpenAICompatibleChatClient(provider)
    result = await client.generate_text(
        build_messages("你好，请介绍一下你自己", "你是一个有用的助手"),
        ChatGenerationOptions(temperature=0.3, max_tokens=800),
    )
    print(result.content)


asyncio.run(main())
```

## HTTP 接口

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-ai/DeepSeek-V4-Pro",
    "messages": [
      {"role": "system", "content": "你是一个有用的助手"},
      {"role": "user", "content": "你好，请介绍一下你自己"}
    ]
  }'
```
