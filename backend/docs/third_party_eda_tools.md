# Third-Party EDA Tools

Open-source EDA tool source trees and local binaries must stay out of backend
application packages.

## Folders

```text
backend/third_party/eda_tools/<tool_name>/  # third-party source or unpacked tool
backend/app/eda_tools/                      # backend wrappers and interfaces
temp/eda-tools/                             # runtime work directories and logs
```

## Rules

1. Do not place third-party tool source under `backend/app`.
2. Do not write runtime Verilog, scripts, logs, netlists, or reports into
   `backend/third_party`.
3. Runtime files must be created under `temp/` and removed after validation
   unless a product feature explicitly persists artifacts.
4. Backend wrappers must expose typed Python APIs and HTTP endpoints; callers
   cannot execute tool commands directly.
5. Tool executable paths should be configured with environment variables such
   as `YOSYS_EXECUTABLE`.

Current Yosys source location:

```text
backend/third_party/eda_tools/yosys/
```
