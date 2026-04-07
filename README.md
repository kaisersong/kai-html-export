# kai-html-export

> Export any HTML file to PPTX or PNG, or publish it to a public URL — works with kai-slide-creator, kai-report-creator, or any self-contained HTML. Pixel-perfect image mode for sharing, editable native mode for modification, uses system Chrome by default — no 300MB Chromium download.

A Claude Code skill that converts HTML files into portable formats using a headless browser.

English | [简体中文](README.zh-CN.md)

---

## Live Demo

**Export Comparison:**

| Mode | Visual Fidelity | Text Editable | Best For |
|------|-----------------|---------------|----------|
| **Image Mode** | ⭐⭐⭐⭐⭐ Pixel-perfect | ❌ Rasterized | Sharing, archiving final decks |
| **Native Mode** | ⭐⭐⭐ Simplified | ✅ Full editing | Editing, translating, repurposing |

**Native Mode Supports:**

| Element | Support |
|---------|---------|
| Headings/paragraphs/lists | ✅ Font size, color, bold, alignment |
| Inline text styles | ✅ Bold, italic, strikethrough, color |
| Inline background highlights | ✅ Colored shapes |
| Tables | ✅ Editable cells |
| Images | ✅ Raster layer embedded |
| SVG | ✅ Rasterized to PNG |
| Grid/dot/noise backgrounds | ✅ Auto-detected and rendered |

---

## Design Philosophy

### 1. System Browser First

Uses system Chrome, Edge, or Brave first — no 300MB Chromium download. Falls back to Playwright Chromium only if no system browser is found.

### 2. Dual-Mode Design

**Image Mode** — Screenshot each slide, pixel-perfect, for sharing final versions.

**Native Mode** — Reconstruct as real PPT shapes, text boxes, tables, with editable text for modification and repurposing.

### 3. Graceful Degradation

| Element | Degradation |
|---------|-------------|
| CSS gradients | → Average color fill |
| Box shadows | → Omitted |
| Custom web fonts | → Nearest system font |
| Unsupported DOM/CSS | → Skip safely, no crash |

### 4. CJK Font Compensation

PingFang SC and other CJK fonts render ~15% wider and ~30% taller in Keynote/PowerPoint than in Chrome. Native mode auto-compensates:
- Text boxes with CJK content widened ×1.15
- Condensed font containers widened ×1.30
- Windows mapping to Microsoft YaHei

### 5. Optional URL Sharing

Defaults to Cloudflare Pages (generally more reachable from China), with Vercel fallback. In hosted cloud sandboxes, auto-sharing is disabled with manual-share guidance.

---

## Install

### Claude Code

Tell Claude: "Install https://github.com/kaisersong/kai-html-export"

Or manually:
```bash
git clone https://github.com/kaisersong/kai-html-export ~/.claude/skills/kai-html-export
pip install playwright python-pptx beautifulsoup4 lxml
```

### OpenClaw

```bash
# Via ClawHub (recommended)
clawhub install kai-html-export

# Or manually
git clone https://github.com/kaisersong/kai-html-export ~/.openclaw/skills/kai-html-export
```

> ClawHub page: https://clawhub.ai/skills/kai-html-export

OpenClaw auto-installs all dependencies on first use.

---

## Usage

### Commands

```bash
# PPTX (image mode, default)
/kai-html-export presentation.html

# Explicit PPTX export
/kai-html-export --pptx presentation.html

# Editable PPTX (native mode)
/kai-html-export --pptx --mode native presentation.html

# Full-page screenshot PNG
/kai-html-export --png report.html

# 2× retina PNG
/kai-html-export --png report.html --scale 2

# Publish to share URL (optional)
python scripts/share-html.py presentation.html
python scripts/share-html.py --provider vercel presentation.html
```

If no file is specified, uses the most recently modified `.html` in the current directory.

### Typical Workflows

**Brand Style Migration:**

```bash
# 1. Re-style: slide-creator reads PPTX and migrates to brand theme
/slide-creator --plan "migrate company-deck.pptx to brand style"
/slide-creator --generate
# → branded-deck.html

# 2. Export both modes
/kai-html-export branded-deck.html
# → branded-deck.pptx (pixel-perfect, for sharing)

/kai-html-export --pptx --mode native branded-deck.html
# → branded-deck.pptx (editable text, for editing)
```

**Export Report to PNG:**

```bash
/kai-html-export --png report.html --scale 2
# → report.png (for WeChat/Telegram sharing)
```

**Publish HTML to URL:**

```bash
# Default Cloudflare Pages
python scripts/share-html.py presentation.html

# Or use Vercel
python scripts/share-html.py --provider vercel presentation.html
```

---

## Features

### Export Modes

- **Image Mode** — Screenshot each slide, pixel-perfect, 16:9 (1440×900)
- **Native Mode** — Real PPT shapes, text boxes, tables, editable text
- **PNG Export** — Full-page screenshot, supports 2× resolution

### Native Mode Supported Elements

| Element | Support |
|---------|---------|
| Headings, paragraphs, lists | ✅ Font size, color, bold, alignment |
| Inline text styles | ✅ Bold, italic, strikethrough, color |
| Inline background highlights | ✅ `<span style="background:…">` |
| Solid-color shapes | ✅ Rectangle fill |
| Tables | ✅ Editable cells and borders |
| Images | ✅ Raster layer embedded |
| SVG graphics | ✅ Rasterized to PNG |
| Grid/dot/noise backgrounds | ✅ Auto-detected and rendered |
| `position:fixed` nav | ✅ Per-slide state computed |

### Native Mode Simplifications

| Element | Behavior |
|---------|----------|
| CSS gradients | → Average color |
| Box shadows | → Omitted |
| Custom web fonts | → System font substitution |
| Unsupported DOM/CSS | → Skip safely |

### URL Sharing

- **Default Cloudflare Pages** — More reachable from China
- **Vercel fallback** — Optional backup provider
- **Sandbox disabled** — Manual-share guidance in hosted sandboxes
- **CLI-only deps** — No install-time dependencies added

---

## Requirements

| Dependency | Purpose | Auto-installed |
|------------|---------|----------------|
| Python 3 + `playwright` | Headless browser screenshots | ✅ |
| Python 3 + `python-pptx` | Assemble PPTX | ✅ |
| `beautifulsoup4` + `lxml` | HTML parsing | ✅ |
| Node.js + Wrangler / Vercel CLI | Optional: URL publishing | ❌ |

**Browser:** System Chrome, Edge, or Brave preferred.

**Cloudflare publishing:**
```bash
wrangler login
```

**Vercel publishing:**
```bash
npx vercel login
```

---

## Compatibility

| Platform | Version | Install path |
|----------|---------|--------------|
| Claude Code | any | `~/.claude/skills/kai-html-export/` |
| OpenClaw | ≥ 0.9 | `~/.openclaw/skills/kai-html-export/` |

**Works With:**

| Skill | Output | Export Format |
|-------|--------|---------------|
| kai-slide-creator | HTML presentation | PPTX (per-slide) |
| kai-report-creator | Single-page HTML report | PNG (full-page) |
| Any HTML file | Self-contained HTML | PPTX or PNG |

---

## Version History

**v1.2.0** — Unified share entry `share-html.py`: default Cloudflare Pages, Vercel fallback, sandbox auto-sharing disabled.

**v1.1.7** — Native mode image fixes: CSS animation wrapper images no longer skipped; `object-fit: contain/fill` images embedded directly.

**v1.1.6** — Post-export preview grid; PPTX structural validation; browser launch sandbox adaptation; QA process documented.

**v1.1.0** — Native mode CJK font compensation: text boxes ×1.15, Condensed ×1.30, Windows Microsoft YaHei mapping.

**v1.0.0** — Initial release: image mode PPTX export, PNG full-page screenshot.