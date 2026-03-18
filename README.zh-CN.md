# kai-html-export

[English](README.md) | 简体中文

> 将任意 HTML 文件导出为 PPTX 或 PNG——适用于 kai-slide-creator、kai-report-creator 或任何独立 HTML 文件。

一个 Claude Code 技能，通过无头浏览器将 HTML 文件转换为可分享的格式。无需 Node.js，使用你已安装的系统 Chrome。

**v1.0.2** — Bug 修复：PPTX 导出现在能正确处理 scroll-snap。使用 `locator().screenshot()` 替代 `window.scrollTo()`，防止使用 `scroll-snap-type: y mandatory` 的 HTML 演示文稿出现幻灯片错位。

## 安装

### Claude Code

```bash
git clone https://github.com/kaisersong/kai-html-export ~/.claude/skills/kai-html-export
pip install playwright python-pptx
```

### OpenClaw / ClawHub

```bash
clawhub install kai-html-export
```

> ClawHub 页面：https://clawhub.ai/skills/kai-html-export

OpenClaw 首次使用时会自动安装依赖（Playwright、python-pptx）。

---

## 使用方法

```
/kai-html-export [file.html]          # 将 HTML 演示文稿导出为 PPTX
/kai-html-export --pptx [file.html]   # 明确指定 PPTX 导出
/kai-html-export --png [file.html]    # 全页截图保存为 PNG
/kai-html-export --png --scale 2      # 2× 高清 PNG
```

未指定文件时，默认使用当前目录中最近修改的 `.html` 文件。

---

## 导出为 PPTX

检测 HTML 中的 `.slide` 元素，逐张截图后合成为 PowerPoint 文件。

```bash
# kai-slide-creator 生成的演示文稿
/kai-html-export presentation.html
# → presentation.pptx（16:9，1440×900）
```

自定义尺寸：
```bash
/kai-html-export presentation.html --width 1920 --height 1080
```

---

## 导出为 PNG

截取完整页面为 PNG 图片，适合将报告或单页 HTML 以图片形式分享。

```bash
# kai-report-creator 生成的报告
/kai-html-export --png report.html
# → report.png

# 2× 分辨率，适合发送到微信/Telegram 等 IM
/kai-html-export --png report.html --scale 2
```

---

## 依赖要求

| 依赖 | 用途 | OpenClaw 自动安装 |
|------|------|------------------|
| Python 3 + `playwright` | 无头浏览器截图 | ✅ via uv |
| Python 3 + `python-pptx` | 合成 PPTX 文件 | ✅ via uv |

**浏览器：** 优先使用系统已安装的 Chrome、Edge 或 Brave，无需下载 Chromium。找不到系统浏览器时才回退到 Playwright 自带的 Chromium。

**Claude Code 用户** 需手动安装：
```bash
pip install playwright python-pptx
```

---

## 适配的技能

| 技能 | 输出类型 | 导出格式 |
|------|---------|---------|
| [kai-slide-creator](https://github.com/kaisersong/slide-creator) | 含 `.slide` 元素的 HTML 演示文稿 | PPTX（逐幻灯片） |
| [kai-report-creator](https://github.com/kaisersong/kai-report-creator) | 单页 HTML 报告 | PNG（全页截图） |
| 任意 HTML 文件 | 独立 HTML | PPTX 或 PNG |

---

## 兼容性

| 平台 | 版本 | 安装路径 |
|------|------|----------|
| Claude Code | 任意 | `~/.claude/skills/kai-html-export/` |
| OpenClaw | ≥ 0.9 | `~/.openclaw/skills/kai-html-export/` |

---

## 许可证

MIT
