# HTML Export Eval Failure Map

Use this map when `scripts/run-skill-evals.py` fails. Each failure code points
to the layer that should be fixed.

## Outcome

Typical failures:
- `outcome.missing_expected_artifact`
- `outcome.expected_extension_missing`
- `outcome.share_url_missing`

Fix here:
- `scripts/export-pptx.py`
- `scripts/export-native-pptx.py`
- `scripts/screenshot.py`
- `scripts/share-html.py`

## Process

Typical failures:
- `process.skill_contract_not_observed`
- `process.export_flow_not_observed`
- `process.expected_action_not_observed`
- `process.validation_not_observed`

Fix here:
- `SKILL.md`
- `README.md`
- `README.zh-CN.md`
- Agent instructions that route to this skill.

## Style

For this skill, Style means format fit and export-quality intent, not prose tone.

Typical failures:
- `style.unrequested_html_generation`
- `style.expected_action_not_observed`
- `style.rubric_missing`

Fix here:
- `SKILL.md`
- `evals/skill-prompts/*.md`
- `tests/fixtures/skill-evals/*-style-rubric.json`

## Efficiency

Typical failures:
- `efficiency.shell_command_count_over_budget`
- `efficiency.repeated_failed_command`
- `efficiency.input_tokens_over_budget`
- `efficiency.output_tokens_over_budget`

Fix here:
- Skill routing instructions.
- Runner adapter normalization.
- Prompt budgets in `evals/html-export-skill-prompts.csv`.

## Operating Rule

Every real production export failure should become one focused eval case before
the behavior is changed.
