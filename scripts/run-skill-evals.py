#!/usr/bin/env python3
"""Run captured-run skill evals for kai-html-export."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


NORMALIZED_TRACE_REQUIRED_FIELDS = [
    "runner",
    "trace_format_version",
    "tool_calls",
    "shell_commands",
    "failed_shell_commands",
    "read_paths",
    "write_paths",
    "artifact_paths",
    "share_urls",
    "wall_ms",
    "run_completed",
    "skill_evidence",
    "runner_warnings",
]

NORMALIZED_TRACE_ARRAY_FIELDS = [
    "tool_calls",
    "shell_commands",
    "failed_shell_commands",
    "read_paths",
    "write_paths",
    "artifact_paths",
    "share_urls",
    "runner_warnings",
]


@dataclass(frozen=True)
class NormalizedTraceMetrics:
    runner: str
    trace_format_version: str
    tool_calls: list[dict[str, Any]]
    shell_commands: list[str]
    failed_shell_commands: list[str]
    read_paths: list[str]
    write_paths: list[str]
    artifact_paths: list[str]
    share_urls: list[str]
    input_tokens: int | None
    output_tokens: int | None
    wall_ms: int
    run_completed: bool
    skill_evidence: dict[str, bool]
    runner_warnings: list[str]


@dataclass(frozen=True)
class SkillEvalCase:
    case_id: str
    total_score: int
    passed: bool
    eval_complete: bool
    scores: dict[str, int]
    failures: list[str]
    style_rubric: dict[str, Any] | None
    metrics: dict[str, Any]
    artifact_dir: str


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def bool_field(row: dict[str, str], key: str) -> bool:
    return row[key].strip().lower() == "true"


def int_field(row: dict[str, str], key: str, default: int) -> int:
    value = row.get(key, "").strip()
    return int(value) if value else default


def _suffix_match(paths: list[str], suffix: str) -> bool:
    normalized_suffix = suffix.replace("\\", "/").lstrip("./")
    return any(path.replace("\\", "/").lstrip("./").endswith(normalized_suffix) for path in paths)


def _contains_any(values: list[str], needles: list[str]) -> bool:
    haystack = "\n".join(values)
    return any(needle in haystack for needle in needles)


def _infer_paths_from_command(command: str) -> list[str]:
    return re.findall(
        r"(?:SKILL\.md|README(?:\.zh-CN)?\.md|scripts/[^\s'\";]+\.py|tests/[^\s'\";]+\.py)",
        command,
    )


def _infer_artifacts_from_command(command: str) -> list[str]:
    return re.findall(r"[^\s'\";]+\.(?:pptx|png|txt)", command)


def _infer_share_urls(text: str) -> list[str]:
    return re.findall(r"https://[^\s'\"<>]+(?:pages\.dev|vercel\.app|clawhub\.ai)[^\s'\"<>]*", text)


def _is_failed_shell_command(command: str, exit_code: Any) -> bool:
    if exit_code in (None, 0):
        return False
    if exit_code == 1 and re.search(r"(^|[\s'\"])(rg|ripgrep)(\s|$)", command):
        return False
    return True


def _infer_skill_evidence(
    read_paths: list[str],
    write_paths: list[str],
    artifact_paths: list[str],
    share_urls: list[str],
    commands: list[str],
) -> dict[str, bool]:
    all_paths = read_paths + write_paths + artifact_paths
    skill_contract_read = _suffix_match(read_paths, "SKILL.md") or _contains_any(commands, ["SKILL.md"])
    pptx_export_observed = (
        _contains_any(commands, ["scripts/export-pptx.py", "export-pptx.py"])
        or any(path.endswith(".pptx") for path in all_paths)
    )
    png_export_observed = (
        _contains_any(commands, ["scripts/screenshot.py", "screenshot.py"])
        or any(path.endswith(".png") for path in all_paths)
    )
    share_flow_observed = (
        _contains_any(
            commands,
            ["scripts/share-html.py", "share-html.py", "deploy-cloudflare.py", "deploy-vercel.py", "wrangler", "vercel"],
        )
        or bool(share_urls)
    )
    validation_observed = _contains_any(
        commands,
        [
            "scripts/verify-pptx.py",
            "verify-pptx.py",
            "tests/test_pptx.py",
            "tests/test_screenshot.py",
            "tests/test_share_deploy.py",
            "Image.open",
            "python-pptx",
        ],
    )
    export_flow_observed = pptx_export_observed or png_export_observed or share_flow_observed
    return {
        "skill_contract_read": skill_contract_read,
        "export_flow_observed": export_flow_observed,
        "pptx_export_observed": pptx_export_observed,
        "png_export_observed": png_export_observed,
        "share_flow_observed": share_flow_observed,
        "validation_observed": validation_observed,
    }


def validate_normalized_trace_payload(payload: dict[str, Any], path: Path) -> None:
    missing = [field for field in NORMALIZED_TRACE_REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"{path}: normalized trace missing required field(s): {', '.join(missing)}")
    if payload.get("trace_format_version") != "normalized-v1":
        raise ValueError(f"{path}: normalized trace must use trace_format_version='normalized-v1'")
    if not isinstance(payload.get("runner"), str) or not payload.get("runner", "").strip():
        raise ValueError(f"{path}: normalized trace runner must be a non-empty string")
    for field in NORMALIZED_TRACE_ARRAY_FIELDS:
        if not isinstance(payload.get(field), list):
            raise ValueError(f"{path}: normalized trace field {field!r} must be an array")
    if not isinstance(payload.get("skill_evidence"), dict):
        raise ValueError(f"{path}: normalized trace field 'skill_evidence' must be an object")
    if not isinstance(payload.get("run_completed"), bool):
        raise ValueError(f"{path}: normalized trace field 'run_completed' must be a boolean")
    wall_ms = payload.get("wall_ms")
    if not isinstance(wall_ms, int) or wall_ms < 0:
        raise ValueError(f"{path}: normalized trace field 'wall_ms' must be a non-negative integer")


def load_normalized_trace(path: Path) -> NormalizedTraceMetrics:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_normalized_trace_payload(payload, path)
    return NormalizedTraceMetrics(
        runner=str(payload["runner"]),
        trace_format_version=str(payload["trace_format_version"]),
        tool_calls=list(payload.get("tool_calls") or []),
        shell_commands=list(payload.get("shell_commands") or []),
        failed_shell_commands=list(payload.get("failed_shell_commands") or []),
        read_paths=list(payload.get("read_paths") or []),
        write_paths=list(payload.get("write_paths") or []),
        artifact_paths=list(payload.get("artifact_paths") or []),
        share_urls=list(payload.get("share_urls") or []),
        input_tokens=payload.get("input_tokens"),
        output_tokens=payload.get("output_tokens"),
        wall_ms=int(payload.get("wall_ms") or 0),
        run_completed=bool(payload.get("run_completed", True)),
        skill_evidence=dict(payload.get("skill_evidence") or {}),
        runner_warnings=list(payload.get("runner_warnings") or []),
    )


def normalize_codex_events(events: list[dict[str, Any]], wall_ms: int = 0) -> NormalizedTraceMetrics:
    shell_commands: list[str] = []
    failed_shell_commands: list[str] = []
    read_paths: list[str] = []
    write_paths: list[str] = []
    artifact_paths: list[str] = []
    share_urls: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    runner_warnings: list[str] = []
    input_tokens: int | None = None
    output_tokens: int | None = None

    for event in events:
        usage = event.get("usage")
        if isinstance(usage, dict):
            if usage.get("input_tokens") is not None:
                input_tokens = int(usage["input_tokens"])
            if usage.get("output_tokens") is not None:
                output_tokens = int(usage["output_tokens"])

        item = event.get("item")
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type == "error":
            message = str(item.get("message") or "")
            runner_warnings.append(f"codex.event_error:{message[:120]}")
            continue
        if item_type == "command_execution":
            command = str(item.get("command") or "")
            if event.get("type") == "item.completed" and command:
                shell_commands.append(command)
                read_paths.extend(_infer_paths_from_command(command))
                inferred_artifacts = _infer_artifacts_from_command(command)
                artifact_paths.extend(inferred_artifacts)
                write_paths.extend(inferred_artifacts)
                share_urls.extend(_infer_share_urls(command + "\n" + str(item.get("aggregated_output") or "")))
                exit_code = item.get("exit_code")
                if _is_failed_shell_command(command, exit_code):
                    failed_shell_commands.append(command)
            tool_calls.append(
                {
                    "type": "command_execution",
                    "command": command,
                    "exit_code": item.get("exit_code"),
                    "status": item.get("status"),
                }
            )
            continue
        if item_type == "file_read":
            path = str(item.get("path") or "")
            if path:
                read_paths.append(path)
        elif item_type == "file_write":
            path = str(item.get("path") or "")
            if path:
                write_paths.append(path)
                if path.endswith((".pptx", ".png", ".txt")):
                    artifact_paths.append(path)

    skill_evidence = _infer_skill_evidence(read_paths, write_paths, artifact_paths, share_urls, shell_commands)
    return NormalizedTraceMetrics(
        runner="codex",
        trace_format_version="codex-jsonl-v1",
        tool_calls=tool_calls,
        shell_commands=shell_commands,
        failed_shell_commands=failed_shell_commands,
        read_paths=sorted(set(read_paths)),
        write_paths=sorted(set(write_paths)),
        artifact_paths=sorted(set(artifact_paths)),
        share_urls=sorted(set(share_urls)),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        wall_ms=wall_ms,
        run_completed=True,
        skill_evidence=skill_evidence,
        runner_warnings=runner_warnings,
    )


def _subprocess_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _normalize_partial_codex_output(raw_trace_path: Path, output: Any, wall_ms: int) -> NormalizedTraceMetrics:
    raw_trace_path.parent.mkdir(parents=True, exist_ok=True)
    raw_trace_path.write_text(_subprocess_text(output), encoding="utf-8")
    try:
        metrics = normalize_codex_events(read_jsonl(raw_trace_path), wall_ms=wall_ms)
    except json.JSONDecodeError as exc:
        return NormalizedTraceMetrics(
            runner="codex",
            trace_format_version="codex-jsonl-v1",
            tool_calls=[],
            shell_commands=[],
            failed_shell_commands=[],
            read_paths=[],
            write_paths=[],
            artifact_paths=[],
            share_urls=[],
            input_tokens=None,
            output_tokens=None,
            wall_ms=wall_ms,
            run_completed=False,
            skill_evidence=_infer_skill_evidence([], [], [], [], []),
            runner_warnings=[f"codex.partial_trace_decode_error:{str(exc)[:120]}"],
        )
    return NormalizedTraceMetrics(**(asdict(metrics) | {"run_completed": False}))


def _resolve_existing_path(root: Path, path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else root / path


def _display_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _relative_artifact_dir(root: Path, artifact_dir: Path) -> str:
    try:
        return str(artifact_dir.relative_to(root))
    except ValueError:
        return str(artifact_dir)


def artifact_files_for_case(
    root: Path,
    metrics: NormalizedTraceMetrics,
    artifact_dir: Path,
    expected_artifact: str,
) -> list[Path]:
    if expected_artifact not in {"pptx", "png"}:
        return []

    extension = "." + expected_artifact
    candidates: list[Path] = []
    candidates.extend(sorted(artifact_dir.rglob(f"*{extension}")) if artifact_dir.exists() else [])
    for path_text in metrics.artifact_paths + metrics.write_paths:
        if not path_text.endswith(extension):
            continue
        path = _resolve_existing_path(root, path_text)
        if path.exists() and path not in candidates:
            candidates.append(path)
    return candidates


def share_urls_for_case(root: Path, metrics: NormalizedTraceMetrics) -> list[str]:
    urls = list(metrics.share_urls)
    for path_text in metrics.artifact_paths:
        path = _resolve_existing_path(root, path_text)
        if path.exists():
            urls.extend(_infer_share_urls(path.read_text(encoding="utf-8", errors="replace")))
    return sorted(set(urls))


def _has_any_output(metrics: NormalizedTraceMetrics) -> bool:
    outputs = metrics.artifact_paths + metrics.write_paths + metrics.share_urls
    return bool(outputs) or bool(metrics.skill_evidence.get("export_flow_observed"))


def expected_action_observed(row: dict[str, str], metrics: NormalizedTraceMetrics) -> bool:
    expected_action = row.get("expected_action", "").strip()
    commands = "\n".join(metrics.shell_commands)
    if expected_action == "pptx-image":
        return bool(metrics.skill_evidence.get("pptx_export_observed")) and "--mode native" not in commands
    if expected_action == "pptx-native":
        return bool(metrics.skill_evidence.get("pptx_export_observed")) and "--mode native" in commands
    if expected_action == "png":
        return bool(metrics.skill_evidence.get("png_export_observed"))
    if expected_action == "share":
        return bool(metrics.skill_evidence.get("share_flow_observed"))
    return False


def default_style_rubric_fixture(root: Path, case_id: str) -> Path:
    return root / "tests" / "fixtures" / "skill-evals" / f"{case_id}-style-rubric.json"


def _validate_style_rubric(rubric: dict[str, Any], case_id: str) -> list[str]:
    failures: list[str] = []
    required = ["case_id", "overall_pass", "score", "checks", "summary"]
    for key in required:
        if key not in rubric:
            failures.append(f"style.rubric_missing_{key}")

    if rubric.get("case_id") != case_id:
        failures.append("style.rubric_case_mismatch")
    score = rubric.get("score")
    if not isinstance(score, int) or score < 0 or score > 100:
        failures.append("style.rubric_score_invalid")
    if not isinstance(rubric.get("overall_pass"), bool):
        failures.append("style.rubric_overall_pass_invalid")
    checks = rubric.get("checks")
    if not isinstance(checks, list) or len(checks) < 4:
        failures.append("style.rubric_checks_invalid")
    elif any(
        not isinstance(check, dict)
        or not isinstance(check.get("id"), str)
        or not isinstance(check.get("pass"), bool)
        or not isinstance(check.get("score"), int)
        or not 1 <= check.get("score", 0) <= 5
        or not isinstance(check.get("notes"), str)
        or not check.get("notes", "").strip()
        for check in checks
    ):
        failures.append("style.rubric_check_invalid")
    if not isinstance(rubric.get("summary"), str) or not rubric.get("summary", "").strip():
        failures.append("style.rubric_summary_invalid")
    return failures


def style_rubric_path_for_case(
    root: Path,
    case_id: str,
    artifact_dir: Path,
    allow_fixture_style_rubric: bool,
) -> tuple[Path | None, str | None]:
    artifact_path = artifact_dir / "style-rubric.json"
    if artifact_path.exists():
        return artifact_path, "artifact"
    fixture_path = default_style_rubric_fixture(root, case_id)
    if allow_fixture_style_rubric and fixture_path.exists():
        return fixture_path, "fixture"
    return None, None


def score_outcome(
    root: Path,
    row: dict[str, str],
    metrics: NormalizedTraceMetrics,
    artifact_dir: Path,
) -> tuple[int, list[str]]:
    failures: list[str] = []
    should_trigger = bool_field(row, "should_trigger")
    expected_artifact = row.get("expected_artifact", "").strip()

    if not should_trigger:
        if _has_any_output(metrics):
            return 0, ["outcome.negative_case_generated_export"]
        return 25, []

    if expected_artifact == "url":
        urls = share_urls_for_case(root, metrics)
        if not urls:
            return 0, ["outcome.share_url_missing"]
        score = 15
        if metrics.skill_evidence.get("share_flow_observed"):
            score += 5
        else:
            failures.append("outcome.share_flow_not_observed")
        if metrics.skill_evidence.get("validation_observed") and not metrics.failed_shell_commands:
            score += 5
        else:
            failures.append("outcome.share_validation_not_observed")
        return score, failures

    artifact_files = artifact_files_for_case(root, metrics, artifact_dir, expected_artifact)
    if not artifact_files:
        return 0, ["outcome.missing_expected_artifact"]

    score = 10
    expected_extension = "." + expected_artifact
    if any(path.suffix == expected_extension for path in artifact_files):
        score += 5
    else:
        failures.append("outcome.expected_extension_missing")
    if metrics.skill_evidence.get("validation_observed"):
        score += 5
    else:
        failures.append("outcome.validation_not_observed")
    if not metrics.failed_shell_commands:
        score += 5
    else:
        failures.append("outcome.failed_command_present")
    return score, failures


def score_process(row: dict[str, str], metrics: NormalizedTraceMetrics) -> tuple[int, list[str]]:
    failures: list[str] = []
    should_trigger = bool_field(row, "should_trigger")
    if not should_trigger:
        if metrics.skill_evidence.get("export_flow_observed"):
            return 0, ["process.negative_case_used_export_flow"]
        return 25, []

    score = 0
    if metrics.skill_evidence.get("skill_contract_read") or _suffix_match(metrics.read_paths, "SKILL.md"):
        score += 5
    else:
        failures.append("process.skill_contract_not_observed")

    if any(_suffix_match(metrics.read_paths, path) for path in ["README.md", "README.zh-CN.md"]) or any(
        path.startswith("scripts/") for path in metrics.read_paths
    ):
        score += 5
    else:
        failures.append("process.export_reference_not_observed")

    if metrics.skill_evidence.get("export_flow_observed"):
        score += 5
    else:
        failures.append("process.export_flow_not_observed")

    if expected_action_observed(row, metrics):
        score += 5
    else:
        failures.append("process.expected_action_not_observed")

    if metrics.skill_evidence.get("validation_observed"):
        score += 5
    else:
        failures.append("process.validation_not_observed")

    return score, failures


def score_style(
    root: Path,
    row: dict[str, str],
    metrics: NormalizedTraceMetrics,
    artifact_dir: Path,
    allow_fixture_style_rubric: bool,
) -> tuple[int, list[str], dict[str, Any] | None]:
    failures: list[str] = []
    if not bool_field(row, "should_trigger"):
        return 25, [], None

    score = 0
    if expected_action_observed(row, metrics):
        score += 5
    else:
        failures.append("style.expected_action_not_observed")

    if metrics.skill_evidence.get("validation_observed") or row.get("expected_artifact") == "url":
        score += 5
    else:
        failures.append("style.validation_or_share_evidence_missing")

    if not any(path.endswith(".html") for path in metrics.write_paths):
        score += 5
    else:
        failures.append("style.unrequested_html_generation")

    style_rubric = None
    rubric_path, rubric_source = style_rubric_path_for_case(
        root,
        row["id"],
        artifact_dir,
        allow_fixture_style_rubric,
    )
    if rubric_path is not None and rubric_source is not None:
        rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
        rubric_failures = _validate_style_rubric(rubric, row["id"])
        if rubric_failures:
            failures.extend(rubric_failures)
            failures.append("eval.style_rubric_invalid")
        else:
            score += round(int(rubric.get("score", 0)) * 10 / 100)
        style_rubric = {
            "source": rubric_source,
            "path": _display_path(root, rubric_path),
            "score": int(rubric.get("score", 0)) if isinstance(rubric.get("score"), int) else None,
            "overall_pass": bool(rubric.get("overall_pass")),
        }
        if not rubric.get("overall_pass"):
            failures.append("style.rubric_needs_work")
    else:
        failures.append("style.rubric_missing")
        failures.append("eval.style_rubric_missing")

    return min(score, 25), failures, style_rubric


def score_efficiency(row: dict[str, str], metrics: NormalizedTraceMetrics) -> tuple[int, list[str]]:
    failures: list[str] = []
    score = 25
    max_shell_commands = int_field(row, "max_shell_commands", 8)
    max_input_tokens = int_field(row, "max_input_tokens", 60000)
    max_output_tokens = int_field(row, "max_output_tokens", 12000)
    max_wall_ms = int_field(row, "max_wall_ms", 120000)

    if len(metrics.shell_commands) > max_shell_commands:
        score -= 5
        failures.append("efficiency.shell_command_count_over_budget")

    failed_counts = Counter(metrics.failed_shell_commands)
    repeated_failed = sum(count - 1 for count in failed_counts.values() if count > 1)
    if metrics.failed_shell_commands:
        score -= 5
        failures.append("efficiency.failed_shell_command")
    if repeated_failed:
        score -= 10
        failures.append("efficiency.repeated_failed_command")

    if metrics.input_tokens is not None and metrics.input_tokens > max_input_tokens:
        score -= 5
        failures.append("efficiency.input_tokens_over_budget")
    if metrics.output_tokens is not None and metrics.output_tokens > max_output_tokens:
        score -= 5
        failures.append("efficiency.output_tokens_over_budget")
    if metrics.wall_ms > max_wall_ms:
        score -= 3
        failures.append("efficiency.wall_time_over_budget")

    return max(score, 0), failures


def default_normalized_fixture(root: Path, case_id: str) -> Path:
    return root / "tests" / "fixtures" / "skill-evals" / f"{case_id}-normalized.json"


def render_live_eval_prompt(root: Path, row: dict[str, str], artifact_dir: Path) -> str:
    prompt_text = (root / row["prompt_path"]).read_text(encoding="utf-8")
    relative_artifact_dir = _relative_artifact_dir(root, artifact_dir)
    prompt_text = prompt_text.replace("{artifact_dir}", f"`{relative_artifact_dir}`")
    return (
        "You are running a development eval for the local kai-html-export skill.\n"
        "Before deciding or exporting, read `SKILL.md` and follow it as the source of truth.\n"
        "Keep the run efficient: load only files that materially help this case, avoid broad repo searches, "
        "and do not regenerate source HTML content.\n\n"
        + prompt_text
        + "\n\nEval harness constraints:\n"
        + f"- Save export artifacts or captured share evidence exactly under `{relative_artifact_dir}`.\n"
        + "- If this request belongs to another skill, do not create PPTX, PNG, HTML, or share artifacts.\n"
        + "- If you export PPTX or PNG, run a lightweight validation step.\n"
        + "- If live sharing is unsafe or disabled, preserve sandbox safety and capture the manual-share evidence.\n"
    )


def run_codex_live(root: Path, row: dict[str, str], raw_trace_path: Path, artifact_dir: Path) -> NormalizedTraceMetrics:
    eval_prompt = render_live_eval_prompt(root, row, artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "codex",
        "exec",
        "--json",
        "--cd",
        str(root),
        "--sandbox",
        "workspace-write",
        "--ephemeral",
        "-",
    ]
    timeout_seconds = int_field(row, "max_wall_ms", 120000) / 1000
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            input=eval_prompt,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        wall_ms = round((time.perf_counter() - started) * 1000)
        metrics = _normalize_partial_codex_output(raw_trace_path, exc.output, wall_ms)
        stderr = _subprocess_text(exc.stderr).strip()
        warnings = list(metrics.runner_warnings)
        warnings.insert(0, f"codex.timeout:{timeout_seconds:.1f}s")
        if stderr:
            warnings.append(f"codex.stderr:{stderr[:160]}")
        return NormalizedTraceMetrics(**(asdict(metrics) | {"runner_warnings": warnings}))
    wall_ms = round((time.perf_counter() - started) * 1000)
    raw_trace_path.parent.mkdir(parents=True, exist_ok=True)
    raw_trace_path.write_text(completed.stdout, encoding="utf-8")
    events = read_jsonl(raw_trace_path)
    metrics = normalize_codex_events(events, wall_ms=wall_ms)
    warnings = list(metrics.runner_warnings)
    if completed.returncode != 0:
        warnings.append(f"codex.returncode:{completed.returncode}")
    if completed.stderr.strip():
        warnings.append(f"codex.stderr:{completed.stderr.strip()[:160]}")
    return NormalizedTraceMetrics(
        **(asdict(metrics) | {"run_completed": completed.returncode == 0, "runner_warnings": warnings})
    )


def metrics_for_case(
    root: Path,
    row: dict[str, str],
    runner: str,
    artifact_dir: Path,
    normalized_trace: Path | None,
    raw_trace: Path | None,
    run_live: bool,
) -> NormalizedTraceMetrics:
    case_id = row["id"]
    if normalized_trace is not None:
        return load_normalized_trace(normalized_trace)
    if runner == "fixture":
        return load_normalized_trace(default_normalized_fixture(root, case_id))
    if raw_trace is not None:
        if runner != "codex":
            raise SystemExit(
                "Raw trace normalization is runner-specific; for generic agents provide --normalized-trace"
            )
        return normalize_codex_events(read_jsonl(raw_trace), wall_ms=0)
    if run_live:
        if runner != "codex":
            raise SystemExit(
                "Live agent execution is not part of the generic harness; "
                "capture the run externally and pass --normalized-trace"
            )
        return run_codex_live(root, row, artifact_dir / "trace.raw.jsonl", artifact_dir)
    if runner == "trace":
        raise SystemExit("--runner trace requires --normalized-trace")
    raise ValueError("Use --runner fixture, --normalized-trace, --raw-trace, or --run-live.")


def evaluate_case(
    root: Path,
    row: dict[str, str],
    runner: str,
    artifact_root: Path,
    normalized_trace: Path | None,
    raw_trace: Path | None,
    run_live: bool,
    allow_fixture_style_rubric: bool,
) -> SkillEvalCase:
    case_id = row["id"]
    case_artifact_dir = artifact_root / case_id
    case_artifact_dir.mkdir(parents=True, exist_ok=True)
    metrics = metrics_for_case(root, row, runner, case_artifact_dir, normalized_trace, raw_trace, run_live)

    normalized_path = case_artifact_dir / "trace.normalized.json"
    normalized_path.write_text(json.dumps(asdict(metrics), ensure_ascii=False, indent=2), encoding="utf-8")

    outcome, outcome_failures = score_outcome(root, row, metrics, case_artifact_dir)
    process, process_failures = score_process(row, metrics)
    style, style_failures, style_rubric = score_style(
        root,
        row,
        metrics,
        case_artifact_dir,
        allow_fixture_style_rubric,
    )
    efficiency, efficiency_failures = score_efficiency(row, metrics)
    scores = {
        "outcome": outcome,
        "process": process,
        "style": style,
        "efficiency": efficiency,
    }
    runner_failures = [] if metrics.run_completed else ["runner.run_incomplete"]
    failures = runner_failures + outcome_failures + process_failures + style_failures + efficiency_failures
    total_score = sum(scores.values())
    should_trigger = bool_field(row, "should_trigger")
    outcome_gate = outcome >= 20 if should_trigger else outcome == 25
    eval_complete = metrics.run_completed and not any(failure.startswith("eval.") for failure in failures)
    passed = eval_complete and outcome_gate and total_score >= 75 and not any(
        failure in {
            "outcome.negative_case_generated_export",
            "process.negative_case_used_export_flow",
        }
        for failure in failures
    )

    return SkillEvalCase(
        case_id=case_id,
        total_score=total_score,
        passed=passed,
        eval_complete=eval_complete,
        scores=scores,
        failures=failures,
        style_rubric=style_rubric,
        metrics=asdict(metrics),
        artifact_dir=str(case_artifact_dir),
    )


def selected_rows(rows: list[dict[str, str]], case_id: str | None) -> list[dict[str, str]]:
    if case_id is None:
        return rows
    selected = [row for row in rows if row["id"] == case_id]
    if not selected:
        raise SystemExit(f"No eval case found for {case_id!r}")
    return selected


def build_payload(cases: list[SkillEvalCase]) -> dict[str, Any]:
    categories = ["outcome", "process", "style", "efficiency"]
    return {
        "cases": [asdict(case) for case in cases],
        "summary": {
            "total": len(cases),
            "passed": sum(1 for case in cases if case.passed),
            "failed": sum(1 for case in cases if not case.passed),
            "incomplete": sum(1 for case in cases if not case.eval_complete),
            "average_score": round(sum(case.total_score for case in cases) / len(cases), 2) if cases else 0,
            "average_category_scores": {
                category: round(sum(case.scores[category] for case in cases) / len(cases), 2) if cases else 0
                for category in categories
            },
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument("--manifest", default="evals/html-export-skill-prompts.csv")
    parser.add_argument(
        "--runner",
        choices=["fixture", "trace", "codex"],
        default="fixture",
        help=(
            "fixture replays checked-in normalized traces; trace scores any agent-produced normalized-v1 JSON; "
            "codex is an optional adapter for Codex raw/live traces"
        ),
    )
    parser.add_argument("--case-id", help="Run one case id.")
    parser.add_argument("--normalized-trace", help="Use one normalized-v1 trace for the selected case.")
    parser.add_argument("--raw-trace", help="Normalize and score one raw runner trace for selected case.")
    parser.add_argument("--artifact-dir", default="evals/artifacts/current/skill-runs")
    parser.add_argument("--run-live", action="store_true", help="Invoke the selected live runner.")
    parser.add_argument(
        "--disable-fixture-style-rubric",
        action="store_true",
        help="Do not use checked-in style rubric fixtures when scoring fixture runs.",
    )
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--json-out", help="Optional JSON output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    manifest = (root / args.manifest).resolve()
    artifact_root = Path(args.artifact_dir)
    artifact_root = artifact_root if artifact_root.is_absolute() else root / artifact_root
    normalized_trace = Path(args.normalized_trace).resolve() if args.normalized_trace else None
    raw_trace = Path(args.raw_trace).resolve() if args.raw_trace else None

    rows = selected_rows(load_manifest(manifest), args.case_id)
    if (normalized_trace or raw_trace) and len(rows) != 1:
        raise SystemExit("--normalized-trace and --raw-trace require --case-id to select exactly one case")

    try:
        cases = [
            evaluate_case(
                root,
                row,
                args.runner,
                artifact_root,
                normalized_trace,
                raw_trace,
                args.run_live,
                args.runner == "fixture" and not args.disable_fixture_style_rubric,
            )
            for row in rows
        ]
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    payload = build_payload(cases)

    if args.json_out:
        target = Path(args.json_out)
        target = target if target.is_absolute() else root / target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for case in cases:
            status = "PASS" if case.passed else "FAIL"
            print(f"{status} {case.case_id}: {case.total_score}/100 {case.scores}")
            for failure in case.failures:
                print(f"  - {failure}")
        print(f"Summary: {payload['summary']['passed']} passed, {payload['summary']['failed']} failed.")
    return 0 if payload["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
