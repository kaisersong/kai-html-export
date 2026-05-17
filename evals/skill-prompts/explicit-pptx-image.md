Use the $kai-html-export skill to export an existing HTML slide deck to PPTX.

Input:
- HTML file: `tests/fixtures/simple_slides.html`
- Output directory: {artifact_dir}

Requirements:
- Use PPTX image mode.
- Save exactly one `.pptx` file under the output directory.
- Do not rewrite or regenerate the slide content.
- Run a lightweight validation step after export.
