# Agent Tool Examples

This folder stores examples for backend-controlled project tools.

Example manifest files belong in `../manifests` and use the `*.tool.json`
suffix. Runtime executors should not live in the manifest file; they should be
mapped by the backend allowlist so the model can request a tool but never run
shell, SQL, filesystem, or network operations directly.
