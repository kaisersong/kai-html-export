Use the $kai-html-export skill with no explicit filename.

Setup assumption:
- The working directory contains multiple `.html` files.
- The most recently modified file is the intended input.
- Output directory: {artifact_dir}

Requirements:
- Follow the skill default: choose the most recently modified `.html`.
- Export it to PPTX image mode.
- Save exactly one `.pptx` file under the output directory.
- Do not ask the user to choose unless the local file state is ambiguous.
