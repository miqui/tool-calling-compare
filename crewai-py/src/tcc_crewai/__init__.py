"""CrewAI track of tool-calling-compare."""

import os

# Keyless/offline by default: no telemetry or tracing prompts. Must run before `import crewai`.
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
