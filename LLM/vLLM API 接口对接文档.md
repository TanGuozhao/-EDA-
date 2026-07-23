# vLLM API 接口对接文档

## EDA 教学大模型 - vLLM OpenAI 兼容接口对接文档

### 1. 基础服务信息

1. 服务部署环境：AutoDL 24G 单卡，vLLM 0.4.2
2. 加载模型：Qwen2.5-7B-Instruct-AWQ
3. 公网访问地址（外部开发使用）

```
公网访问地址，控制台->自定义服务->查看所租用服务器的公网IP
```

- 容器内部本地地址（服务器批量测评使用）

```
http://127.0.0.1:6006/v1
```

- 鉴权 API Key

```
eda-dev-key-2026
```

- 模型标识（调用时 model 字段固定填写）

```
qwen2.5-7b-eda
```

### 2. 鉴权规则

所有请求必须携带请求头：

```
Authorization: Bearer eda-dev-key-2026
```

不携带 / 密钥错误 → 返回 401 Unauthorized。

### 3. 核心接口说明

#### 接口 1：查询当前加载模型

- 请求地址：`GET /v1/models`
- 用途：校验服务是否正常连通
- curl 示例：

```bash
curl "https://u929078-9659-ea0648dd.bjb1.seetacloud.com:8443/v1/models" \
-H "Authorization: Bearer eda-dev-key-2026"
```

#### 接口 2：对话生成接口（核心业务接口）

地址：`POST /v1/chat/completions`

支持 4 类 EDA 业务：知识问答、Verilog 代码生成、自动出题、答题自动判分

##### 通用请求参数

| 参数        | 说明                              | 推荐值                                |
| :---------- | :-------------------------------- | :------------------------------------ |
| model       | 固定模型名                        | qwen2.5-7b-eda                        |
| messages    | 对话上下文数组，[{role, content}] | 用户提问 / 历史对话                   |
| temperature | 随机性，代码场景调低              | 代码 0.2，问答 0.3~0.4                |
| max_tokens  | 单次最大输出长度                  | 800~1200                              |
| stream      | 是否流式逐字返回                  | true = 前端打字效果；false 一次性返回 |

##### 场景 1：单轮 EDA 知识问答（非流式）

Python 调用示例

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://u929078-9659-ea0648dd.bjb1.seetacloud.com:8443/v1",
    api_key="eda-dev-key-2026"
)

resp = client.chat.completions.create(
    model="qwen2.5-7b-eda",
    messages=[{"role":"user","content":"建立时间和保持时间的区别？"}],
    temperature=0.3,
    max_tokens=800,
    stream=False
)
print(resp.choices[0].message.content)
```

##### 场景 2：Verilog 代码生成（流式输出，前端交互）

```python
stream = client.chat.completions.create(
    model="qwen2.5-7b-eda",
    messages=[{"role":"user","content":"写8位同步计数器"}],
    temperature=0.2,
    max_tokens=1024,
    stream=True
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

##### 场景 3：多轮连续对话（学生多次提问）

```python
history = [
    {"role":"user","content":"什么是两级寄存器同步？"},
    {"role":"assistant","content":"用于单比特跨时钟域同步..."},
    {"role":"user","content":"那异步FIFO适用什么场景？"}
]
resp = client.chat.completions.create(
    model="qwen2.5-7b-eda",
    messages=history
)
```

### 4. 业务场景调用规范

1. **知识问答**：temperature=0.3，保证专业准确
2. **Verilog 代码生成**：temperature=0.2，减少随机错误，保证可综合
3. **自动出题**：temperature=0.4，多样化题目
4. **自动判分**：temperature=0.1，严格标准化打分

### 5. 常见问题说明

1. 本地电脑调用失败：检查 API Key、公网地址是否完整；
2. 返回 401：请求头缺少 Authorization；
3. 输出代码语法错误：降低 temperature；
4. AutoDL 关机后接口无法访问：实例仅开发调试开机，无 7×24 常驻服务。

### 6. 配套文件

1. `api_test_client.py`：完整可运行测试代码；
2. `start_vllm_server.sh`：`vllm`服务启动脚本。


