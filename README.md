# kai-html-export

English | [简体中文](README.zh-CN.md)

> Export any HTML file to PPTX or PNG — works with kai-slide-creator, kai-report-creator, or any self-contained HTML.

A Claude Code skill that converts HTML files into portable formats using a headless browser. No Node.js required — uses your existing system Chrome.

**v1.1.6** — Four improvements borrowed from the Anthropic PPTX skill: (1) post-export preview grid (`{name}-preview.png`) with thumbnails of slides 1, ~1/3, ~2/3, and last — no manual Keynote inspection needed; (2) structural PPTX validation after save — slide count mismatch and unreadable slides are reported as `⚠` warnings; (3) sandbox-safe browser launch for native mode — tries Chrome → Edge → Chromium → Playwright bundled Chromium, adds `--no-sandbox` automatically on Linux/Docker/CI; (4) QA process documented in SKILL.md.

---

## Install

### Claude Code

```bash
git clone https://github.com/kaisersong/kai-html-export ~/.claude/skills/kai-html-export
pip install playwright python-pptx beautifulsoup4 lxml
```

### OpenClaw / ClawHub

```bash
clawhub install kai-html-export
```

> ClawHub page: https://clawhub.ai/skills/kai-html-export

Dependencies are installed automatically by OpenClaw on first use.

---

## Usage

```
/kai-html-export [file.html]                    # PPTX (image mode, default)
/kai-html-export --pptx [file.html]             # Explicit PPTX export
/kai-html-export --pptx --mode native [file]    # Editable PPTX (native mode)
/kai-html-export --png [file.html]              # Full-page screenshot to PNG
/kai-html-export --png --scale 2                # 2× retina-quality PNG
```

If no file is specified, the most recently modified `.html` in the current directory is used.

---

## Export Modes

### Image Mode (default)

Captures each slide as a pixel-perfect screenshot and assembles them into a PowerPoint file. Text is rasterized — not editable, but visually identical to the browser.

```bash
/kai-html-export presentation.html
# → presentation.pptx  (16:9, 1440×900)
```

| | Image Mode |
|--|--|
| Visual fidelity | ⭐⭐⭐⭐⭐ pixel-perfect |
| Text editable | ❌ rasterized |
| Best for | sharing, archiving final decks |

---

### Native Mode — Editable PPTX

Reconstructs each slide as real PowerPoint shapes, text boxes, and tables. Text is fully editable in Keynote and PowerPoint.

```bash
/kai-html-export --pptx --mode native presentation.html
# → presentation.pptx  (editable text, shapes, tables)
```

| | Native Mode |
|--|--|
| Visual fidelity | ⭐⭐⭐ simplified |
| Text editable | ✅ full text editing |
| Best for | editing content, translating, repurposing slides |

#### What native mode renders

| Element | Support |
|---------|---------|
| Headings, paragraphs, lists | ✅ with font size, color, bold, alignment |
| Inline text styles | ✅ bold, italic, strikethrough, color |
| Inline background highlights | ✅ `<span style="background:…">` → colored shape behind text |
| Solid-color shapes (div with background) | ✅ rectangles with fill |
| Tables | ✅ editable cells with borders |
| Images (`<img>`, `canvas`, CSS `background-image`) | ✅ inserted as raster layers |
| SVG graphics | ✅ rasterized to PNG and embedded |
| Grid / dot / noise backgrounds | ✅ auto-detected and rendered |
| `position:fixed` nav dots + progress bars | ✅ per-slide state computed from slide index; set `data-export-progress="false"` on `<body>` to suppress both |

#### What native mode approximates or skips

| Element | Behavior |
|---------|---------|
| CSS gradients | → solid color (average of gradient stops) |
| Box shadows | → omitted |
| Custom web fonts (e.g. Barlow, Inter) | → nearest system font |
| Unsupported DOM / CSS edge cases | → skipped safely instead of crashing the export |

#### CJK (Chinese / Japanese / Korean) compensation

PingFang SC and other CJK fonts render ~15% wider and ~30% taller in Keynote/PowerPoint than in Chrome. Native mode automatically compensates:

- Text boxes with CJK content are widened by ×1.15
- Condensed font containers (Barlow Condensed, etc.) are widened by ×1.30
- Width expansion only applies to boxes narrower than 3 inches (prevents wide containers from overflowing)
- CJK system font mapping prefers Microsoft YaHei on Windows so exported PPTs do not fall back to Calibri
- Inline background shapes use PPTX coordinate system (not Chrome coordinates) to stay aligned with text

---

## Export to PNG

Captures the full rendered page as a PNG — useful for sharing reports or single-page HTML as images.

```bash
/kai-html-export --png report.html
# → report.png

# 2× resolution for retina / messaging apps
/kai-html-export --png report.html --scale 2
```

---

## Requirements

| Dependency | Purpose | Auto-installed (OpenClaw) |
|-----------|---------|--------------------------|
| Python 3 + `playwright` | Headless browser screenshots | ✅ via uv |
| Python 3 + `python-pptx` | Assemble PPTX | ✅ via uv |
| `beautifulsoup4` + `lxml` | HTML parsing (native mode) | ✅ via uv |

**Browser:** Uses system Chrome, Edge, or Brave first — no 300MB Chromium download. Falls back to Playwright Chromium if no system browser is found.

**Claude Code users** — install manually:
```bash
pip install playwright python-pptx beautifulsoup4 lxml
```

---

## Works With

| Skill | Output | Export format |
|-------|--------|--------------|
| [kai-slide-creator](https://github.com/kaisersong/slide-creator) | HTML presentation with `.slide` elements | PPTX (slide-by-slide) |
| [kai-report-creator](https://github.com/kaisersong/kai-report-creator) | Single-page HTML report | PNG (full page) |
| Any HTML file | Self-contained HTML | PPTX or PNG |

---

## Compatibility

| Platform | Version | Install path |
|---------|---------|-------------|
| Claude Code | any | `~/.claude/skills/kai-html-export/` |
| OpenClaw | ≥ 0.9 | `~/.openclaw/skills/kai-html-export/` |

---

## License

MIT
