Use the $kai-html-export skill to export an existing HTML slide deck to an editable PPTX.

Input:
- HTML file: `tests/fixtures/native_raster_elements.html`
- Output directory: {artifact_dir}

Requirements:
- Use native mode so text and supported shapes remain editable.
- Save exactly one `.pptx` file under the output directory.
- Do not rasterize the entire deck unless native mode fails.
- Run a lightweight validation step after export.
