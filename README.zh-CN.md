# kai-html-export

[English](README.md) | 简体中文

> 将任意 HTML 文件导出为 PPTX 或 PNG——适用于 kai-slide-creator、kai-report-creator 或任何独立 HTML 文件。

一个 Claude Code 技能，通过无头浏览器将 HTML 文件转换为可分享的格式。无需 Node.js，使用你已安装的系统 Chrome。

**v1.1.3** — Native 模式：inline 背景色块、condensed 字体检测、CJK 宽度补偿、fixed-chrome 导航点。

---

## 安装

### Claude Code

```bash
git clone https://github.com/kaisersong/kai-html-export ~/.claude/skills/kai-html-export
pip install playwright python-pptx beautifulsoup4 lxml
```

### OpenClaw / ClawHub

```bash
clawhub install kai-html-export
```

> ClawHub 页面：https://clawhub.ai/skills/kai-html-export

OpenClaw 首次使用时会自动安装所有依赖。

---

## 使用方法

```
/kai-html-export [file.html]                    # PPTX（图片模式，默认）
/kai-html-export --pptx [file.html]             # 明确指定 PPTX 导出
/kai-html-export --pptx --mode native [file]    # 可编辑 PPTX（native 模式）
/kai-html-export --png [file.html]              # 全页截图保存为 PNG
/kai-html-export --png --scale 2                # 2× 高清 PNG
```

未指定文件时，默认使用当前目录中最近修改的 `.html` 文件。

---

## 导出模式

### 图片模式（默认）

将每张幻灯片截图后合成为 PowerPoint 文件，与浏览器显示效果像素级一致。文字为图片，不可编辑。

```bash
/kai-html-export presentation.html
# → presentation.pptx（16:9，1440×900）
```

| | 图片模式 |
|--|--|
| 视觉还原度 | ⭐⭐⭐⭐⭐ 像素级一致 |
| 文字可编辑 | ❌ 已光栅化 |
| 适用场景 | 分享、归档最终版演示文稿 |

---

### Native 模式——可编辑 PPTX

将每张幻灯片还原为真实的 PowerPoint 形状、文本框和表格，文字在 Keynote 和 PowerPoint 中完全可编辑。

```bash
/kai-html-export --pptx --mode native presentation.html
# → presentation.pptx（文字、形状、表格均可编辑）
```

| | Native 模式 |
|--|--|
| 视觉还原度 | ⭐⭐⭐ 简化渲染 |
| 文字可编辑 | ✅ 完整文字编辑 |
| 适用场景 | 修改内容、翻译、复用幻灯片 |

#### Native 模式支持的元素

| 元素 | 支持情况 |
|------|---------|
| 标题、段落、列表 | ✅ 字号、颜色、加粗、对齐 |
| 行内文字样式 | ✅ 加粗、斜体、删除线、颜色 |
| 行内背景高亮 | ✅ `<span style="background:…">` → 文字底部彩色色块 |
| 纯色背景形状（带背景色的 div） | ✅ 矩形填充 |
| 表格 | ✅ 可编辑单元格和边框 |
| 图片 | ✅ 原生嵌入 |
| 网格 / 圆点 / 噪点背景 | ✅ 自动检测并渲染 |
| `position:fixed` 导航点和进度条 | ✅ 按幻灯片序号计算每页状态 |

#### Native 模式的简化或跳过项

| 元素 | 处理方式 |
|------|---------|
| CSS 渐变 | → 取渐变中间色填充 |
| Box shadow | → 省略 |
| 自定义 Web 字体（Barlow、Inter 等） | → 替换为最接近的系统字体 |
| SVG 图形 | → 光栅化为 PNG |

#### CJK（中日韩）字体补偿

PingFang SC 等 CJK 字体在 Keynote/PowerPoint 中比 Chrome 宽约 15%、高约 30%。Native 模式会自动补偿：

- 含 CJK 文字的文本框宽度扩大 ×1.15
- Condensed 字体容器（Barlow Condensed 等）扩大 ×1.30
- 宽度扩展仅适用于宽度小于 3 英寸的小框（防止宽容器溢出边界）
- 行内背景色块使用 PPTX 坐标系（而非 Chrome 坐标），确保与文字精确对齐

---

## 导出为 PNG

截取完整页面为 PNG 图片，适合将报告或单页 HTML 以图片形式分享。

```bash
/kai-html-export --png report.html
# → report.png

# 2× 分辨率，适合发送到微信 / Telegram 等 IM
/kai-html-export --png report.html --scale 2
```

---

## 依赖要求

| 依赖 | 用途 | OpenClaw 自动安装 |
|------|------|------------------|
| Python 3 + `playwright` | 无头浏览器截图 | ✅ via uv |
| Python 3 + `python-pptx` | 合成 PPTX | ✅ via uv |
| `beautifulsoup4` + `lxml` | HTML 解析（native 模式） | ✅ via uv |

**浏览器：** 优先使用系统已安装的 Chrome、Edge 或 Brave，无需下载 Chromium。找不到系统浏览器时才回退到 Playwright 自带的 Chromium。

**Claude Code 用户** 需手动安装：
```bash
pip install playwright python-pptx beautifulsoup4 lxml
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
