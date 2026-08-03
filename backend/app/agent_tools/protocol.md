# Project Tool Protocol

## 1. Definitions

- Agent: a model-backed or rule-backed worker that can request tools through
  the backend orchestrator.
- Skill: an optional capability package that changes prompts, allowed tools,
  and result presentation rules.
- Tool: a backend-controlled capability with a manifest, schema validation,
  ownership checks, timeout limits, output truncation, and audit logs.
- Orchestrator: the backend component that decides whether a requested tool
  call is allowed and maps it to a fixed executor.

## 2. Manifest

Each tool must provide a `*.tool.json` manifest with:

- `tool_id`: stable namespaced id, for example `eda.example_inspect`.
- `name`, `version`, `description`.
- `allowed_agents` and `allowed_skills`: callers allowed to request this tool.
- `input_schema` and `output_schema`: JSON Schema objects.
- `timeout_seconds` and `max_output_chars`.
- `requires_login`, `risk_level`, `visibility`, `owner`, `enabled`.
- `audit_version`: schema/audit contract version.

## 3. Runtime Request

The orchestrator accepts only this normalized request shape:

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

Before execution, the backend must check:

1. The tool exists and is enabled.
2. The user is authenticated when `requires_login` is true.
3. `agent_id` and optional `skill_id` are allowed by the manifest.
4. `arguments` pass JSON Schema validation.
5. The requested resources belong to the user/session/course/project scope.
6. High-risk tools have explicit confirmation when required.
7. Execution uses a fixed backend allowlist entry, not model-provided commands.

## 4. Runtime Result

Executors return only normalized `AgentToolResult` data:

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

Allowed statuses are `ok`, `error`, `timeout`, and `denied`.

## 5. Security Rules

- The model cannot execute shell, SQL, filesystem paths, or network calls.
- User-provided scripts, project files, Makefiles, Tcl files, and shell
  commands are data, not executable instructions.
- Tools that call local programs must run through backend-defined executors with
  isolated workspaces, timeouts, resource limits, and no-network defaults.
- Hidden references, private datasets, secret prompts, raw filesystem paths,
  credentials, and internal logs must never be returned to the frontend or
  model unless explicitly marked public.
- Tool output must be truncated to `max_output_chars`.

## 6. Audit Record

Every attempted call, including denied calls, must write:

- `request_id`, `tool_id`, `user_id`, `session_id`, `agent_id`, `skill_id`.
- argument summary, not raw secrets or full large files.
- result summary, status, error code, elapsed time.
- related resource ids and timestamp.

## 7. Executor Binding

Manifest files describe permission and schema contracts only. They do not define
how to execute a tool.

Executors must be registered in backend code through an allowlist. The
orchestrator maps `tool_id` to exactly one executor implementation and rejects
unknown, disabled, or unauthorized tools.
