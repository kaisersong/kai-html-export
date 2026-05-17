import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "run-skill-evals.py"
FIXTURES = ROOT / "tests" / "fixtures" / "skill-evals"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("run_skill_evals", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_script(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(ROOT), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_prompt_manifest_paths_exist():
    manifest = ROOT / "evals" / "html-export-skill-prompts.csv"
    assert manifest.exists()
    rows = manifest.read_text(encoding="utf-8").splitlines()[1:]
    assert len(rows) == 7
    for line in rows:
        fields = line.split(",")
        assert (ROOT / fields[3]).is_file(), fields[3]


def test_external_eval_manifests_cover_required_categories():
    required_counts = {
        "golden_cases.yaml": 10,
        "exception_cases.yaml": 5,
        "permission_cases.yaml": 3,
        "adversarial_cases.yaml": 3,
        "tool_failure_cases.yaml": 3,
        "context_bloat_cases.yaml": 1,
        "multi_skill_cases.yaml": 1,
    }
    for filename, minimum in required_counts.items():
        text = (ROOT / "evals" / filename).read_text(encoding="utf-8")
        assert text.count("\n  - id: ") >= minimum, filename


def test_fixture_runner_scores_all_cases_with_four_categories(tmp_path: Path):
    result = run_script(
        "--runner",
        "fixture",
        "--artifact-dir",
        str(tmp_path),
        "--format",
        "json",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["summary"]["total"] == 7
    assert payload["summary"]["passed"] == 7
    assert payload["summary"]["failed"] == 0
    assert payload["summary"]["average_score"] >= 95
    for category in ["outcome", "process", "style", "efficiency"]:
        assert category in payload["summary"]["average_category_scores"]
        assert payload["summary"]["average_category_scores"][category] > 0


def test_fixture_runner_scores_pptx_success_case_and_style_fixture(tmp_path: Path):
    result = run_script(
        "--runner",
        "fixture",
        "--case-id",
        "explicit-pptx-image",
        "--normalized-trace",
        str(FIXTURES / "explicit-pptx-image-normalized.json"),
        "--artifact-dir",
        str(tmp_path),
        "--format",
        "json",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    case = payload["cases"][0]
    assert case["scores"] == {
        "outcome": 25,
        "process": 25,
        "style": 25,
        "efficiency": 25,
    }
    assert case["total_score"] == 100
    assert case["passed"] is True
    assert case["eval_complete"] is True
    assert case["style_rubric"]["source"] == "fixture"
    assert case["style_rubric"]["score"] >= 90
    assert case["metrics"]["runner"] == "fixture"
    assert len(case["metrics"]["shell_commands"]) == 2
    assert case["metrics"]["input_tokens"] == 9000
    assert case["metrics"]["output_tokens"] == 1800
    assert "style.rubric_missing" not in case["failures"]


def test_trace_runner_scores_generic_agent_normalized_trace(tmp_path: Path):
    trace_payload = json.loads((FIXTURES / "explicit-pptx-image-normalized.json").read_text(encoding="utf-8"))
    trace_payload["runner"] = "qoder"
    trace_payload["trace_format_version"] = "normalized-v1"
    trace = tmp_path / "qoder-normalized.json"
    trace.write_text(json.dumps(trace_payload), encoding="utf-8")

    artifact_root = tmp_path / "artifacts"
    case_artifact_dir = artifact_root / "explicit-pptx-image"
    case_artifact_dir.mkdir(parents=True)
    case_artifact_dir.joinpath("style-rubric.json").write_text(
        (FIXTURES / "explicit-pptx-image-style-rubric.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = run_script(
        "--runner",
        "trace",
        "--case-id",
        "explicit-pptx-image",
        "--normalized-trace",
        str(trace),
        "--artifact-dir",
        str(artifact_root),
        "--format",
        "json",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    case = payload["cases"][0]
    assert case["passed"] is True
    assert case["metrics"]["runner"] == "qoder"
    assert case["metrics"]["trace_format_version"] == "normalized-v1"
    assert case["style_rubric"]["source"] == "artifact"


def test_trace_runner_requires_normalized_trace(tmp_path: Path):
    result = run_script(
        "--runner",
        "trace",
        "--case-id",
        "negative-slide-generation",
        "--artifact-dir",
        str(tmp_path),
        "--format",
        "json",
    )

    assert result.returncode == 1
    assert "--runner trace requires --normalized-trace" in result.stderr


def test_trace_runner_rejects_non_normalized_trace_version(tmp_path: Path):
    trace_payload = json.loads((FIXTURES / "explicit-pptx-image-normalized.json").read_text(encoding="utf-8"))
    trace_payload["runner"] = "claude-code"
    trace_payload["trace_format_version"] = "codex-jsonl-v1"
    trace = tmp_path / "wrong-version.json"
    trace.write_text(json.dumps(trace_payload), encoding="utf-8")

    result = run_script(
        "--runner",
        "trace",
        "--case-id",
        "explicit-pptx-image",
        "--normalized-trace",
        str(trace),
        "--artifact-dir",
        str(tmp_path / "artifacts"),
        "--format",
        "json",
    )

    assert result.returncode == 1
    assert "normalized trace must use trace_format_version='normalized-v1'" in result.stderr


def test_positive_case_without_style_rubric_is_eval_incomplete(tmp_path: Path):
    result = run_script(
        "--runner",
        "fixture",
        "--case-id",
        "explicit-pptx-image",
        "--normalized-trace",
        str(FIXTURES / "explicit-pptx-image-normalized.json"),
        "--artifact-dir",
        str(tmp_path),
        "--disable-fixture-style-rubric",
        "--format",
        "json",
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    case = payload["cases"][0]
    assert case["scores"]["style"] == 15
    assert case["total_score"] == 90
    assert case["passed"] is False
    assert case["eval_complete"] is False
    assert "style.rubric_missing" in case["failures"]
    assert "eval.style_rubric_missing" in case["failures"]


def test_negative_case_allows_skill_contract_read_for_routing(tmp_path: Path):
    result = run_script(
        "--runner",
        "fixture",
        "--case-id",
        "negative-slide-generation",
        "--normalized-trace",
        str(FIXTURES / "negative-slide-generation-normalized.json"),
        "--artifact-dir",
        str(tmp_path),
        "--format",
        "json",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    case = payload["cases"][0]
    assert case["scores"] == {
        "outcome": 25,
        "process": 25,
        "style": 25,
        "efficiency": 25,
    }
    assert case["total_score"] == 100
    assert case["passed"] is True


def test_outcome_hard_gate_prevents_process_only_success(tmp_path: Path):
    result = run_script(
        "--runner",
        "fixture",
        "--case-id",
        "explicit-pptx-image",
        "--normalized-trace",
        str(FIXTURES / "missing-artifact-normalized.json"),
        "--artifact-dir",
        str(tmp_path),
        "--format",
        "json",
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    case = payload["cases"][0]
    assert case["passed"] is False
    assert case["scores"]["outcome"] == 0
    assert case["scores"]["process"] == 25
    assert "outcome.missing_expected_artifact" in case["failures"]


def test_codex_raw_trace_normalizes_real_command_events(tmp_path: Path):
    result = run_script(
        "--runner",
        "codex",
        "--case-id",
        "negative-slide-generation",
        "--raw-trace",
        str(FIXTURES / "real-codex-tool-smoke.jsonl"),
        "--artifact-dir",
        str(tmp_path),
        "--format",
        "json",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    case = payload["cases"][0]
    assert case["metrics"]["runner"] == "codex"
    assert case["metrics"]["shell_commands"] == ["/bin/zsh -lc pwd"]
    assert case["metrics"]["input_tokens"] == 38572
    assert case["metrics"]["output_tokens"] == 384
    assert "codex.event_error" in case["metrics"]["runner_warnings"][0]


def test_codex_rg_no_match_is_not_counted_as_failed_shell_command(tmp_path: Path):
    result = run_script(
        "--runner",
        "codex",
        "--case-id",
        "negative-slide-generation",
        "--raw-trace",
        str(FIXTURES / "real-codex-rg-no-match.jsonl"),
        "--artifact-dir",
        str(tmp_path),
        "--format",
        "json",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    case = payload["cases"][0]
    assert case["metrics"]["failed_shell_commands"] == []
    assert case["scores"]["efficiency"] == 25


def test_codex_live_runner_closes_stdin(monkeypatch, tmp_path: Path):
    module = load_runner_module()
    captured_kwargs = {}
    captured_command = []

    def fake_run(command, **kwargs):
        captured_command.extend(command)
        captured_kwargs.update(kwargs)
        stdout = '{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":1}}\n'
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    module.run_codex_live(
        ROOT,
        {"prompt_path": "evals/skill-prompts/negative-slide-generation.md"},
        tmp_path / "trace.raw.jsonl",
        tmp_path / "artifacts",
    )

    assert captured_command[-1] == "-"
    assert "Create an 8-slide launch deck" in captured_kwargs["input"]
    assert "local kai-html-export skill" in captured_kwargs["input"]


def test_codex_live_timeout_returns_warning(monkeypatch, tmp_path: Path):
    module = load_runner_module()

    def fake_run(command, **kwargs):
        partial = "\n".join(
            [
                '{"type":"item.completed","item":{"type":"command_execution","command":"/bin/zsh -lc pwd","exit_code":0,"status":"completed"}}',
                '{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":2}}',
            ]
        )
        raise subprocess.TimeoutExpired(command, kwargs["timeout"], output=partial, stderr="too slow")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    metrics = module.run_codex_live(
        ROOT,
        {
            "prompt_path": "evals/skill-prompts/negative-slide-generation.md",
            "max_wall_ms": "120000",
        },
        tmp_path / "trace.raw.jsonl",
        tmp_path / "artifacts",
    )

    assert metrics.runner_warnings[0] == "codex.timeout:120.0s"
    assert metrics.run_completed is False
    assert metrics.shell_commands == ["/bin/zsh -lc pwd"]
    assert metrics.input_tokens == 10
    assert metrics.wall_ms >= 0


def test_incomplete_run_cannot_pass_negative_case(tmp_path: Path):
    trace = tmp_path / "timeout-normalized.json"
    trace.write_text(
        json.dumps(
            {
                "runner": "generic-agent",
                "trace_format_version": "normalized-v1",
                "tool_calls": [],
                "shell_commands": [],
                "failed_shell_commands": [],
                "read_paths": [],
                "write_paths": [],
                "artifact_paths": [],
                "share_urls": [],
                "input_tokens": None,
                "output_tokens": None,
                "wall_ms": 120000,
                "run_completed": False,
                "skill_evidence": {
                    "skill_contract_read": False,
                    "export_flow_observed": False,
                    "pptx_export_observed": False,
                    "png_export_observed": False,
                    "share_flow_observed": False,
                    "validation_observed": False,
                },
                "runner_warnings": ["agent.timeout:120.0s"],
            }
        ),
        encoding="utf-8",
    )

    result = run_script(
        "--runner",
        "trace",
        "--case-id",
        "negative-slide-generation",
        "--normalized-trace",
        str(trace),
        "--artifact-dir",
        str(tmp_path / "artifacts"),
        "--format",
        "json",
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    case = payload["cases"][0]
    assert case["passed"] is False
    assert "runner.run_incomplete" in case["failures"]


def test_codex_live_runner_replaces_artifact_dir_placeholder(monkeypatch, tmp_path: Path):
    module = load_runner_module()
    root = tmp_path / "repo"
    root.mkdir()
    (root / "prompt.md").write_text("Save under {artifact_dir}.", encoding="utf-8")
    captured_kwargs = {}

    def fake_run(command, **kwargs):
        captured_kwargs.update(kwargs)
        stdout = '{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":1}}\n'
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    module.run_codex_live(
        root,
        {"prompt_path": "prompt.md"},
        tmp_path / "trace.raw.jsonl",
        root / "artifacts" / "case",
    )

    assert "{artifact_dir}" not in captured_kwargs["input"]
    assert "Save under `artifacts/case`." in captured_kwargs["input"]


def test_readmes_document_captured_run_skill_evals():
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    for marker in [
        "scripts/run-skill-evals.py",
        "--runner fixture",
        "--runner trace",
        "normalized-v1",
        "Outcome",
        "Process",
        "Style",
        "Efficiency",
    ]:
        assert marker in readme_en
    assert "--runner codex" not in readme_en
    for marker in [
        "scripts/run-skill-evals.py",
        "--runner fixture",
        "--runner trace",
        "normalized-v1",
        "Outcome",
        "Process",
        "Style",
        "Efficiency",
        "四类目标",
    ]:
        assert marker in readme_zh
    assert "--runner codex" not in readme_zh


def test_normalized_trace_schema_is_agent_agnostic():
    schema = json.loads((ROOT / "evals" / "normalized-trace.schema.json").read_text(encoding="utf-8"))
    runner_schema = schema["properties"]["runner"]
    assert runner_schema["type"] == "string"
    assert "enum" not in runner_schema
    for key in [
        "runner",
        "trace_format_version",
        "shell_commands",
        "failed_shell_commands",
        "read_paths",
        "write_paths",
        "artifact_paths",
        "share_urls",
        "run_completed",
        "skill_evidence",
    ]:
        assert key in schema["required"]


def test_tests_runner_includes_skill_eval_suite():
    runner = (ROOT / "tests" / "run_tests.py").read_text(encoding="utf-8")
    assert '"evals"' in runner
    assert "test_skill_eval_runner.py" in runner
