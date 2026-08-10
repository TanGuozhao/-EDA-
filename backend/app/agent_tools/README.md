# Project Tool Folder

This package defines the local standard for backend-controlled project tools.

## Structure

```text
agent_tools/
  README.md
  protocol.md
  schemas.py
  registry.py
  manifests/
    *.tool.json
  examples/
```

## Purpose

Tools are backend capabilities that an agent, Skill, or application workflow may
request through an orchestrator. A tool manifest describes what the tool is
allowed to accept and return. The actual executor must remain backend-owned and
allowlisted.

The model must never execute shell commands, SQL, arbitrary paths, local tools,
or network requests directly.
