# kai-html-export

> 将任意 HTML 文件导出为 PPTX、PNG，或发布为公网链接——适用于 kai-slide-creator、kai-report-creator 或任何独立 HTML 文件。图片模式像素级还原，Native 模式文字可编辑，默认使用系统 Chrome 无需下载 Chromium。

一个 Claude Code 技能，通过无头浏览器将 HTML 文件转换为便携格式。

[English](README.md) | 简体中文

---

## 效果展示

**导出对比：**

| 模式 | 视觉还原 | 文字可编辑 | 适用场景 |
|------|----------|------------|----------|
| **图片模式** | ⭐⭐⭐⭐⭐ 像素级 | ❌ 光栅化 | 分享、归档最终版 |
| **Native 模式** | ⭐⭐⭐ 简化渲染 | ✅ 完整编辑 | 修改内容、翻译、复用 |

**Native 模式支持：**

| 元素 | 支持 |
|------|------|
| 标题/段落/列表 | ✅ 字号、颜色、加粗、对齐 |
| 行内样式 | ✅ 加粗、斜体、删除线、颜色 |
| 行内背景高亮 | ✅ 彩色色块 |
| 表格 | ✅ 可编辑单元格 |
| 图片 | ✅ 光栅层嵌入 |
| SVG | ✅ 光栅化为 PNG |
| 网格/圆点/噪点背景 | ✅ 自动检测渲染 |

---

## 设计理念

### 1. 系统浏览器优先

优先使用系统已安装的 Chrome、Edge 或 Brave，无需下载 300MB Chromium。找不到系统浏览器时才回退到 Playwright 自带的 Chromium。

### 2. 双模式设计

**图片模式** — 每张幻灯片截图，像素级一致，适合分享最终版。

**Native 模式** — 还原为真实 PPT 形状、文本框、表格，文字可编辑，适合修改和复用。

### 3. 优雅降级

| 元素 | 降级处理 |
|------|----------|
| CSS 渐变 | → 取中间色填充 |
| Box shadow | → 省略 |
| 自定义 Web 字体 | → 最接近系统字体 |
| 不支持的 DOM/CSS | → 安全跳过，不崩溃 |

### 4. CJK 字体补偿

PingFang SC 等 CJK 字体在 Keynote/PowerPoint 中比 Chrome 宽约 15%、高约 30%。Native 模式自动补偿：
- 含 CJK 文字的文本框宽度扩大 ×1.15
- Condensed 字体容器扩大 ×1.30
- Windows 上映射为 Microsoft YaHei

### 5. 分享链接可选

默认发布到 Cloudflare Pages（在中国通常比 Vercel 更易访问），保留 Vercel 作为回退。在托管云沙箱中禁用自动分享，输出手动分享指引。

---

## 安装

### Claude Code

告诉 Claude：「安装 https://github.com/kaisersong/kai-html-export」

或手动：
```bash
git clone https://github.com/kaisersong/kai-html-export ~/.claude/skills/kai-html-export
pip install playwright python-pptx beautifulsoup4 lxml
```

### OpenClaw

```bash
# 通过 ClawHub 安装（推荐）
clawhub install kai-html-export

# 或手动克隆
git clone https://github.com/kaisersong/kai-html-export ~/.openclaw/skills/kai-html-export
```

> ClawHub 页面：https://clawhub.ai/skills/kai-html-export

OpenClaw 首次使用时会自动安装所有依赖。

---

## 使用方式

### 基本命令

```bash
# PPTX（图片模式，默认）
/kai-html-export presentation.html

# 明确指定 PPTX 导出
/kai-html-export --pptx presentation.html

# 可编辑 PPTX（Native 模式）
/kai-html-export --pptx --mode native presentation.html

# 全页截图 PNG
/kai-html-export --png report.html

# 2× 高清 PNG
/kai-html-export --png report.html --scale 2

# 发布为分享链接（可选）
python scripts/share-html.py presentation.html
python scripts/share-html.py --provider vercel presentation.html
```

未指定文件时，默认使用当前目录中最近修改的 `.html` 文件。

### 典型工作流

**品牌风格迁移：**

```bash
# 1. 风格迁移：slide-creator 读取 PPTX，按品牌主题重排
/slide-creator --plan "将 company-deck.pptx 迁移到品牌风格"
/slide-creator --generate
# → branded-deck.html

# 2. 两种模式同时导出
/kai-html-export branded-deck.html
# → branded-deck.pptx（像素级，用于分享）

/kai-html-export --pptx --mode native branded-deck.html
# → branded-deck.pptx（文字可编辑，用于修改）
```

**报告导出为 PNG：**

```bash
/kai-html-export --png report.html --scale 2
# → report.png（适合发送到微信/Telegram）
```

**发布 HTML 为分享链接：**

```bash
# 默认 Cloudflare Pages
python scripts/share-html.py presentation.html

# 或使用 Vercel
python scripts/share-html.py --provider vercel presentation.html
```

---

## 功能特性

### 导出模式

- **图片模式** — 每张幻灯片截图，像素级还原，16:9 (1440×900)
- **Native 模式** — 真实 PPT 形状、文本框、表格，文字可编辑
- **PNG 导出** — 全页截图，支持 2× 分辨率

### Native 模式支持元素

| 元素 | 支持情况 |
|------|----------|
| 标题、段落、列表 | ✅ 字号、颜色、加粗、对齐 |
| 行内文字样式 | ✅ 加粗、斜体、删除线、颜色 |
| 行内背景高亮 | ✅ `<span style="background:…">` |
| 纯色背景形状 | ✅ 矩形填充 |
| 表格 | ✅ 可编辑单元格和边框 |
| 图片 | ✅ 光栅层嵌入 |
| SVG 图形 | ✅ 光栅化为 PNG |
| 网格/圆点/噪点背景 | ✅ 自动检测渲染 |
| `position:fixed` 导航 | ✅ 按幻灯片计算状态 |

### Native 模式简化项

| 元素 | 处理方式 |
|------|----------|
| CSS 渐变 | → 取渐变中间色 |
| Box shadow | → 省略 |
| 自定义 Web 字体 | → 系统字体替换 |
| 不支持的 DOM/CSS | → 安全跳过 |

### 分享链接

- **默认 Cloudflare Pages** — 在中国通常更易访问
- **Vercel 回退** — 可选备用方案
- **沙箱禁用** — 托管云沙箱中输出手动分享指引
- **依赖 CLI** — 不新增安装时依赖

---

## 依赖要求

| 依赖 | 用途 | OpenClaw 自动安装 |
|------|------|------------------|
| Python 3 + `playwright` | 无头浏览器截图 | ✅ |
| Python 3 + `python-pptx` | 合成 PPTX | ✅ |
| `beautifulsoup4` + `lxml` | HTML 解析 | ✅ |
| Node.js + Wrangler / Vercel CLI | 可选：发布分享链接 | ❌ |

**浏览器：** 优先使用系统 Chrome、Edge 或 Brave。

**Cloudflare 发布：**
```bash
wrangler login
```

**Vercel 发布：**
```bash
npx vercel login
```

---

## 兼容性

| 平台 | 版本 | 安装路径 |
|------|------|----------|
| Claude Code | 任意 | `~/.claude/skills/kai-html-export/` |
| OpenClaw | ≥ 0.9 | `~/.openclaw/skills/kai-html-export/` |

**适配的技能：**

| 技能 | 输出类型 | 导出格式 |
|------|---------|----------|
| kai-slide-creator | HTML 演示文稿 | PPTX（逐幻灯片） |
| kai-report-creator | 单页 HTML 报告 | PNG（全页截图） |
| 任意 HTML 文件 | 独立 HTML | PPTX 或 PNG |

---

## 版本日志

**v1.2.0** — 统一分享入口 `share-html.py`：默认 Cloudflare Pages，保留 Vercel 回退，沙箱禁用自动分享。

**v1.1.7** — Native 模式图片修复：CSS 动画 wrapper 包裹的图片不再被跳过；`object-fit: contain/fill` 图片直接嵌入。

**v1.1.6** — 导出后预览网格；PPTX 结构验证；浏览器启动沙箱适配；QA 流程说明。

**v1.1.0** — Native 模式 CJK 字体补偿：文本框宽度×1.15，Condensed 字体×1.30，Windows 映射 Microsoft YaHei。

**v1.0.0** — 初始发布：图片模式 PPTX 导出，PNG 全页截图。