Use the $kai-html-export skill to export an existing single-page HTML report to PNG.

Input:
- HTML file: `tests/fixtures/report.html`
- Output directory: {artifact_dir}

Requirements:
- Save exactly one `.png` file under the output directory.
- Use scale 2 for a share-ready image.
- Do not convert it to PPTX.
- Run a lightweight validation step after export.
