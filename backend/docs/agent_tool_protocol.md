# 项目 Tool 标准协议

本文档定义本项目通用的 Tool 文件夹与调用协议。它不绑定任何临时任务编号，也不绑定某一个具体业务模块。所有业务能力都应作为同一套协议下的不同 Tool。

## 目录约定

```text
backend/app/agent_tools/
  README.md
  protocol.md
  schemas.py
  registry.py
  manifests/
    *.tool.json
  examples/
```

## 概念

- Agent：由模型或规则驱动的工作单元，只能通过后端编排器请求 Tool。
- Skill：可选能力包，用于补充提示词、限制可用 Tool、定义结果呈现规则。
- Tool：后端受控能力，必须有 manifest、参数 Schema、权限、超时、输出上限和审计。
- Orchestrator：后端编排器，负责鉴权、校验、资源归属检查、风险确认和 executor 映射。
- Executor：后端 allowlist 中的固定实现，真正执行某个 Tool。

## Tool Manifest 必填字段

每个 Tool 使用 `*.tool.json` 声明静态契约：

- `tool_id`：稳定命名空间 ID，例如 `eda.example_inspect`。
- `name`、`version`、`description`。
- `allowed_agents`：允许调用的 Agent ID。
- `allowed_skills`：允许调用的 Skill ID，可为空。
- `input_schema`、`output_schema`：输入输出 JSON Schema。
- `timeout_seconds`、`max_output_chars`。
- `requires_login`、`risk_level`、`visibility`。
- `audit_version`、`owner`、`enabled`。

## 标准请求

```json
{
  "tool_id": "eda.example_inspect",
  "request_id": "req_...",
  "user_id": "1",
  "session_id": "chat_...",
  "agent_id": "default-agent",
  "skill_id": null,
  "arguments": {},
  "confirmation_token": null
}
```

执行前必须检查：

1. Tool 存在且启用。
2. 需要登录时用户已认证。
3. `agent_id` 和可选 `skill_id` 有权限调用该 Tool。
4. `arguments` 通过 JSON Schema 校验。
5. 请求访问的资源属于当前用户、会话、课程或项目范围。
6. 高风险 Tool 已完成必要确认。
7. 执行路径来自后端 allowlist，而不是模型生成的命令。

## 标准结果

```json
{
  "tool_id": "eda.example_inspect",
  "request_id": "req_...",
  "status": "ok",
  "output": {},
  "public_summary": "Tool completed.",
  "sources": [],
  "error": null,
  "elapsed_ms": 1234,
  "truncated": false
}
```

`status` 只能是 `ok`、`error`、`timeout`、`denied`。

## 安全边界

1. 模型不能直接执行 shell、SQL、文件路径或网络请求。
2. 用户上传的脚本、工程文件、Makefile、Tcl、shell 命令都按数据处理，不按指令执行。
3. 调用本地程序的 Tool 必须通过后端 executor，并设置隔离目录、超时、资源限制和默认无网络。
4. 隐藏答案、私有数据集、系统提示词、密钥、原始路径和内部日志默认不可公开。
5. 返回给前端或模型的内容必须经过 `visibility`、`max_output_chars` 和公开摘要规则过滤。

## 审计记录

每次 Tool 调用尝试都必须记录，包括被拒绝的调用：

- `request_id`、`tool_id`、`user_id`、`session_id`、`agent_id`、`skill_id`。
- 参数摘要，不能记录密钥、完整大文件或未脱敏隐私内容。
- 结果摘要、状态、错误码、耗时。
- 关联资源 ID 和创建时间。

## Executor 绑定

Manifest 只描述工具契约，不描述具体执行方式。后端必须在代码中显式注册 executor allowlist。编排器根据 `tool_id` 映射到唯一 executor；未知、禁用、越权或参数非法的 Tool 请求必须拒绝并写审计。

## 当前本地样例

`backend/app/agent_tools/manifests/eda_example_inspect.tool.json` 是一个通用占位样例，用来验证 manifest 加载、Schema 形状和后续 `/api/tools` 接入方式。具体业务 Tool 后续按同一协议单独新增。
