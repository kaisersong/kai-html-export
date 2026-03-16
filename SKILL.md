---
name: kai-html-export
description: Export any HTML file to PPTX or PNG. Use when the user wants to convert an HTML presentation to PowerPoint, screenshot a web page, or export an HTML report as an image. Triggers: /kai-html-export, --pptx, --png, "export to pptx", "screenshot html", "convert html to powerpoint".
version: 1.0.0
metadata: {"openclaw":{"emoji":"📤","os":["darwin","linux","windows"],"requires":{"bins":["python3"]},"install":[{"id":"python-pptx","kind":"uv","package":"python-pptx","label":"python-pptx (PPTX assembly)"},{"id":"playwright","kind":"uv","package":"playwright","label":"Playwright (headless browser for screenshots)"}]}}
---

# kai-html-export

Export any HTML file to PPTX or PNG using a headless browser. No Node.js required — uses your existing system Chrome.

## Commands

| Command | What it does |
|---------|-------------|
| `/kai-html-export [file.html]` | Export HTML presentation to PPTX (auto-detects slides) |
| `/kai-html-export --pptx [file.html]` | Explicit PPTX export |
| `/kai-html-export --png [file.html]` | Full-page screenshot to PNG |
| `/kai-html-export --png --scale 2 [file.html]` | 2× resolution screenshot |

If no file is specified, use the most recently modified `.html` file in the current directory.

## Export to PPTX

Run the bundled script:

```bash
python3 <skill-path>/scripts/export-pptx.py <file.html> [output.pptx] [--width 1440] [--height 900]
```

- Detects `.slide` elements and captures each one as a full-bleed slide
- Uses system Chrome/Edge/Brave first (no download); falls back to Playwright Chromium
- Animations are disabled before capture so all content is visible
- Reports slide count and output path when done

## Export to PNG

Run the bundled script:

```bash
python3 <skill-path>/scripts/screenshot.py <file.html> [output.png] [--width 1440] [--scale 2]
```

- Captures the full page at the specified width
- `--scale 2` produces a 2× retina-quality image
- Useful for sharing reports or single-page HTML as images

## Dependencies

| Package | Purpose | Install |
|---------|---------|---------|
| `playwright` | Headless browser screenshots | `pip install playwright` |
| `python-pptx` | Assemble screenshots into PPTX | `pip install python-pptx` |

No browser download needed if Chrome, Edge, or Brave is already installed.

## Works with any HTML

Designed to work with output from:
- **kai-slide-creator** — HTML presentations with `.slide` elements
- **kai-report-creator** — Single-page HTML reports
- Any self-contained HTML file
