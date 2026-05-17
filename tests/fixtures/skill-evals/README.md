# Captured Runner Trace Fixtures

These fixtures document the normalized metrics consumed by
`scripts/run-skill-evals.py` and the real Codex JSONL shape used by the Codex
adapter tests. Parser support must be based on captured traces like these, not
guessed runner event names.

Observed Codex JSONL shape:

- Top-level events include `thread.started`, `turn.started`, `item.started`,
  `item.completed`, and `turn.completed`.
- Shell commands appear under `item.type == "command_execution"` with
  `command`, `exit_code`, and `status`.
- File reads and writes are not guaranteed in the captured trace; the adapter
  consumes explicit `file_read` and `file_write` items if future traces include
  them.
- Token usage appears on `turn.completed` as `usage.input_tokens` and
  `usage.output_tokens`.
- Runner warnings can come from `item.type == "error"` events, timeout handling,
  or nonzero live runner return codes.

Normalized fixture files use the runner-agnostic `normalized-v1` schema. Unit
tests score normalized metrics directly so ordinary pytest never invokes a live
agent or network-backed deploy runner.
