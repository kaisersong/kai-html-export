# kai-html-export

English | [简体中文](README.zh-CN.md)

> Export any HTML file to PPTX or PNG — works with kai-slide-creator, kai-report-creator, or any self-contained HTML.

A Claude Code skill that converts HTML files into portable formats using a headless browser. No Node.js required — uses your existing system Chrome.

**v1.0.2** — Bug fix: PPTX export now handles scroll-snap correctly. Uses `locator().screenshot()` instead of `window.scrollTo()` to prevent slide misalignment in HTML presentations with `scroll-snap-type: y mandatory`.

## Install

### Claude Code

```bash
git clone https://github.com/kaisersong/kai-html-export ~/.claude/skills/kai-html-export
pip install playwright python-pptx
```

### OpenClaw / ClawHub

```bash
clawhub install kai-html-export
```

> ClawHub page: https://clawhub.ai/skills/kai-html-export

Dependencies (Playwright, python-pptx) are installed automatically by OpenClaw on first use.

---

## Usage

```
/kai-html-export [file.html]          # Export HTML presentation to PPTX
/kai-html-export --pptx [file.html]   # Explicit PPTX export
/kai-html-export --png [file.html]    # Full-page screenshot to PNG
/kai-html-export --png --scale 2      # 2× retina-quality PNG
```

If no file is specified, the most recently modified `.html` in the current directory is used.

---

## Export to PPTX

Detects `.slide` elements in the HTML, captures each one as a pixel-perfect screenshot, and assembles them into a PowerPoint file.

```bash
# Produced by kai-slide-creator
/kai-html-export presentation.html
# → presentation.pptx  (16:9, 1440×900)
```

Custom dimensions:
```bash
/kai-html-export presentation.html --width 1920 --height 1080
```

---

## Export to PNG

Captures the full rendered page as a PNG image — useful for sharing reports or single-page HTML as images.

```bash
# Produced by kai-report-creator
/kai-html-export --png report.html
# → report.png

# 2× resolution for retina / IM sharing
/kai-html-export --png report.html --scale 2
```

---

## Requirements

| Dependency | Purpose | Auto-installed (OpenClaw) |
|-----------|---------|--------------------------|
| Python 3 + `playwright` | Headless browser screenshots | ✅ via uv |
| Python 3 + `python-pptx` | Assemble screenshots into PPTX | ✅ via uv |

**Browser:** Uses system Chrome, Edge, or Brave first — no 300MB Chromium download. Falls back to Playwright Chromium if no system browser is found.

**Claude Code users** — install manually:
```bash
pip install playwright python-pptx
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
