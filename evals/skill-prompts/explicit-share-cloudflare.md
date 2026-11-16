Use the $kai-html-export skill to publish an existing HTML file to a share URL.

Input:
- HTML file: `tests/fixtures/report.html`
- Output directory for captured evidence: {artifact_dir}

Requirements:
- Use the Cloudflare default share flow.
- Preserve sandbox safety: if auto-share is disabled, report the manual-share guidance instead of attempting interactive auth.
- Do not regenerate the report content.
- Capture the resulting URL or manual-share evidence for the eval run.
