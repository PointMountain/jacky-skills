---
name: "pencil-opencli-workflow"
description: "Use when converting a local web page (localhost or file URL) into a Pencil .pen design file. Includes a required `setup` check that verifies `opencli` is installed and Pencil MCP server is configured/enabled before generation."
---

# Pencil OpenCLI Workflow

用于把本地页面（例如 `http://localhost:5173/...`）转成 Pencil `.pen` 设计稿。  
本 skill 提供两个固定指令：`setup` 和 `generate`。

## 1) setup（必须先执行）

当用户说“setup”时，严格按下面顺序执行并汇报结果。

### 1.1 检查 `opencli` 是否安装

```bash
command -v opencli
opencli --help >/dev/null && echo "opencli_ok"
```

如果失败，直接提示用户先安装：

```bash
npm install -g @jackwener/opencli
```

### 1.2 检查 `opencli` 浏览器链路是否可用

```bash
opencli daemon status
opencli browser open about:blank
opencli browser screenshot /tmp/opencli-smoke.png
```

如果失败，提示用户先修复 opencli/browser 环境后再继续。

### 1.3 检查 Pencil MCP server 是否已配置并启用

```bash
codex mcp list
```

验收标准：

- 输出中存在 `pencil`
- `Status` 为 `enabled`

同时检查 server 二进制是否存在：

```bash
ls -la /Users/jiashengwang/.pencil/mcp/cursor/out/mcp-server-darwin-arm64
```

如果任一失败，提示用户先完成 Pencil 安装与 MCP 配置，再继续使用 `generate`。

## 2) generate

当用户说“generate”时，按以下流程执行：

1. 读取用户输入：`url`、`name`、`outDir`（默认 `./pencil`）
2. 使用 opencli 打开目标页面并截图到：
   - `<outDir>/<name>.reference.png`
3. 生成 `.pen` 文件到：
   - `<outDir>/<name>.editable.pen`
4. `.pen` 结构至少包含两层：
   - `reference_layer`：引用 `./<name>.reference.png`
   - `editable_overlay`：可编辑图层（用于后续拆层）
5. 返回最终产物绝对路径

## 3) 生成模板（`.pen` 最小结构）

```json
{
  "version": "2.9",
  "children": [
    {
      "type": "frame",
      "id": "page_root",
      "name": "Generated Editable Base",
      "x": 0,
      "y": 0,
      "width": 1280,
      "height": 720,
      "clip": true,
      "fill": "#020A24",
      "children": [
        {
          "type": "frame",
          "id": "reference_layer",
          "name": "Reference Screenshot",
          "x": 0,
          "y": 0,
          "width": 1280,
          "height": 720,
          "fill": {
            "type": "image",
            "url": "./REPLACE_REFERENCE_FILE",
            "mode": "stretch"
          },
          "opacity": 1
        },
        {
          "type": "frame",
          "id": "editable_overlay",
          "name": "Editable Overlay",
          "x": 0,
          "y": 0,
          "width": 1280,
          "height": 720,
          "fill": "#00000000"
        }
      ]
    }
  ]
}
```

## 4) 输出规范

- 优先返回：
  - setup 检查结果（通过/失败项）
  - 失败时的下一步安装指引
  - 成功时的产物绝对路径
- 不要返回冗长背景说明。
