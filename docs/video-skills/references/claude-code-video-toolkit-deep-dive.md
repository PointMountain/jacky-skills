# claude-code-video-toolkit 深度研究报告

> 研究时间：2026-04-06
> 项目地址：https://github.com/digitalsamba/claude-code-video-toolkit
> Stars：669 | License：MIT | 版本：0.14.1
> 定位：AI 原生视频生产工作区，为 Claude Code 提供创建专业视频所需的全部 Skills、Commands 和 Tools

---

## 目录

1. [项目全景](#一项目全景)
2. [架构设计](#二架构设计)
3. [Skills 系统](#三skills-系统)
4. [Commands 系统](#四commands-系统)
5. [Python Tools 层](#五python-tools-层)
6. [Docker / 云部署](#六docker--云部署)
7. [模板系统](#七模板系统)
8. [品牌系统](#八品牌系统)
9. [共享组件库](#九共享组件库)
10. [风控机制](#十风控机制)
11. [可借鉴的设计模式](#十一可借鉴的设计模式)
12. [参考链接](#十二参考链接)

---

## 一、项目全景

### 1.1 核心能力

```
┌─────────────────────────────────────────────────────────────┐
│                   Claude Code 视频工作区                      │
│                                                             │
│  /setup ──→ /video ──→ /scene-review ──→ /design            │
│               │                          │                  │
│               ▼                          ▼                  │
│         选择模板+品牌             视觉设计精修                  │
│               │                                              │
│               ▼                                              │
│  /generate-voiceover → /record-demo → 渲染输出               │
│               │                          │                  │
│               ▼                          ▼                  │
│         AI 配音/配乐            Playwright 录制 Demo          │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 视频框架 | Remotion (React) | 编程式视频创建 |
| 语音合成 | ElevenLabs / Qwen3-TTS | AI 配音 |
| 图像生成 | FLUX.2 Klein 4B | AI 文生图/图编辑 |
| 视频生成 | LTX-2.3 22B | AI 文生视频/图生视频 |
| 音乐生成 | ACE-Step 1.5 | AI 音乐 |
| 说话人头像 | SadTalker | 静态图片变说话视频 |
| 超分辨率 | Real-ESRGAN | 图片/视频增强 |
| 去水印 | ProPainter | 视频水印去除 |
| 浏览器录制 | Playwright | Demo 视频录制 |
| 云 GPU | Modal (推荐) / RunPod (备选) | GPU 算力 |
| 文件传输 | Cloudflare R2 | 本地与云端文件桥接 |

### 1.3 目录结构

```
claude-code-video-toolkit/
├── .claude/
│   ├── commands/          # 14 个 Slash 命令
│   ├── skills/            # 10 个 Skill 定义
│   └── settings.json
├── tools/                 # 18 个 Python 工具脚本
├── docker/                # 15 个 Docker 部署配置
│   ├── modal-*/           # Modal 部署（8 个）
│   └── runpod-*/          # RunPod 部署（7 个）
├── templates/             # 3 个视频模板
│   ├── product-demo/      # 产品演示
│   ├── sprint-review/     # Sprint 回顾 V1
│   └── sprint-review-v2/  # Sprint 回顾 V2（推荐）
├── brands/                # 品牌配置
│   ├── default/           # 默认品牌
│   └── digital-samba/     # Digital Samba 品牌
├── lib/                   # 共享库
│   ├── components/        # React 共享组件
│   ├── transitions/       # 自定义转场效果
│   ├── theme/             # 主题系统
│   ├── project/           # 项目管理
│   └── brand.ts           # 品牌加载器
├── projects/              # 实际视频项目
├── examples/              # 示例项目
├── showcase/              # 效果展示
├── _internal/             # 内部路线图/日志
├── CLAUDE.md              # Claude Code 全局指导
└── context7.json          # Context7 集成
```

---

## 二、架构设计

### 2.1 四层架构

```
┌──────────────────────────────────────────────────────┐
│  Layer 4: Commands（交互层）                           │
│  /video, /setup, /brand, /template, /scene-review... │
│  用户通过 Slash 命令触发工作流                          │
├──────────────────────────────────────────────────────┤
│  Layer 3: Skills（知识层）                             │
│  remotion, ffmpeg, elevenlabs, frontend-design...    │
│  为 Claude Code 提供领域知识                           │
├──────────────────────────────────────────────────────┤
│  Layer 2: Tools（执行层）                              │
│  cloud_gpu.py, file_transfer.py, flux2.py...         │
│  Python 脚本执行实际的 AI 推理和文件操作                │
├──────────────────────────────────────────────────────┤
│  Layer 1: Templates + Brands（资产层）                 │
│  视频模板 + 品牌配置 + 共享组件库                       │
│  定义了视频的结构和视觉风格                             │
└──────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户输入
  │
  ▼
Command（/video）→ 读取模板 + 品牌配置
  │
  ▼
Skill（remotion）→ Claude Code 生成 React 视频代码
  │
  ▼
Tool（cloud_gpu.py）→ 调用云 GPU 生成 AI 资产
  │                    ├── Modal 同步 POST
  │                    └── RunPod 异步 submit + poll
  │
  ▼
file_transfer.py → R2 上传/下载 → 云端处理
  │
  ▼
Remotion 渲染 → 最终 MP4 输出
```

### 2.3 项目生命周期管理

通过 `project.json` 跟踪多会话视频项目的状态：

```
planning → assets → audio → editing → rendering → complete
   │          │        │        │          │
   ▼          ▼        ▼        ▼          ▼
 场景定义   录制Demo  生成配音   调整时间   最终渲染
 脚本编写   收集素材  生成音乐   预览检查   输出 MP4
```

每个阶段都有对应的 `ProjectPhase` 类型和状态跟踪：

```typescript
export type ProjectPhase =
  | 'planning'   // 场景定义、脚本编写
  | 'assets'     // 录制 Demo、收集素材
  | 'audio'      // 生成配音、音乐
  | 'editing'    // 调整时间、预览
  | 'rendering'  // 最终输出
  | 'complete';  // 完成
```

---

## 三、Skills 系统

项目内嵌 **10 个 Claude Code Skills**，每个 Skill 为 Claude Code 提供特定领域的深度知识。

### 3.1 Skills 清单

| Skill | 状态 | 目录 | 核心职责 |
|-------|------|------|---------|
| **remotion-official** | stable | `.claude/skills/remotion-official/` | Remotion 官方 API 参考（30+ 子文件） |
| **remotion** | stable | `.claude/skills/remotion/` | 工具包特有的 Remotion 模式和约定 |
| **elevenlabs** | stable | `.claude/skills/elevenlabs/` | ElevenLabs TTS、语音克隆、音乐、音效 |
| **ffmpeg** | beta | `.claude/skills/ffmpeg/` | FFmpeg 视频/音频处理 |
| **playwright-recording** | beta | `.claude/skills/playwright-recording/` | Playwright 浏览器录制 |
| **frontend-design** | stable | `.claude/skills/frontend-design/` | 视觉设计优化 |
| **qwen-edit** | stable | `.claude/skills/qwen-edit/` | Qwen 图片编辑提示工程 |
| **acestep** | beta | `.claude/skills/acestep/` | ACE-Step 音乐生成 |
| **ltx2** | beta | `.claude/skills/ltx2/` | LTX-2 视频生成 |
| **runpod** | stable | `.claude/skills/runpod/` | RunPod 云 GPU 配置管理 |

### 3.2 remotion-official（最大最详细的 Skill）

这是从 [remotion-dev/skills](https://github.com/remotion-dev/skills) 同步的官方知识库，包含 30+ 个子文件：

```
.claude/skills/remotion-official/rules/
├── 3d.md                    # 3D 渲染
├── animations.md            # 动画系统
├── audio.md                 # 音频处理
├── audio-visualization.md   # 音频可视化
├── calculate-metadata.md    # 元数据计算
├── charts.md                # 图表组件
├── compositions.md          # 合成管理
├── display-captions.md      # 字幕显示
├── ffmpeg.md                # FFmpeg 集成
├── fonts.md                 # 字体处理
├── gifs.md                  # GIF 支持
├── images.md                # 图片处理
├── lottie.md                # Lottie 动画
├── maps.md                  # 地图组件
├── parameters.md            # 参数传递
├── sequencing.md            # 序列编排
├── subtitles.md             # 字幕生成
├── tailwind.md              # Tailwind 集成
├── text-animations.md       # 文字动画
├── timing.md                # 时间控制
├── transitions.md           # 转场效果
├── transparent-videos.md    # 透明视频
├── trimming.md              # 视频裁剪
├── videos.md                # 视频播放
├── voiceover.md             # 旁白处理
└── assets/                  # 代码示例
    ├── charts-bar-chart.tsx
    ├── text-animations-typewriter.tsx
    └── text-animations-word-highlight.tsx
```

### 3.3 Skill 设计模式

**辅助文件模式**：每个 Skill 除了 SKILL.md 外，还可以包含 `reference.md`、`examples.md`、`parameters.md` 等辅助文件，通过 SKILL.md 中的引用指令加载。

**Skills 分层**：
- `remotion-official`（官方 API 参考） + `remotion`（项目特有模式）两层设计
- 官方知识稳定更新，项目特有知识独立维护

---

## 四、Commands 系统

项目提供 **14 个 Slash 命令**，覆盖视频制作全流程。

### 4.1 命令清单

| 命令 | 用途 | 状态 |
|------|------|------|
| `/setup` | 首次配置（云 GPU、文件传输、语音） | beta |
| `/video` | 视频项目管理（创建/继续/列出） | stable |
| `/brand` | 品牌管理（列出/编辑/创建） | stable |
| `/template` | 模板浏览 | stable |
| `/scene-review` | 逐场景预览（Remotion Studio） | stable |
| `/design` | 聚焦设计精修 | stable |
| `/generate-voiceover` | AI 配音生成 | stable |
| `/record-demo` | Playwright 浏览器录制 | stable |
| `/redub` | 重新配音 | beta |
| `/voice-clone` | 语音克隆 | beta |
| `/skills` | Skill 管理 | stable |
| `/versions` | 版本检查 | stable |
| `/contribute` | 贡献指南 | stable |

### 4.2 核心工作流

```
首次使用:
  /setup → 配置 Modal/RunPod + R2 + ElevenLabs

创建视频:
  /video → 选择模板 → 选择品牌 → 生成项目结构
       → /scene-review → 逐场景预览调整
       → /generate-voiceover → AI 配音
       → /record-demo → 浏览器录制 Demo
       → 渲染输出

品牌管理:
  /brand → 列出品牌 → 编辑/创建品牌配置
```

### 4.3 Command 文件格式

Commands 存放在 `.claude/commands/` 目录，使用 Markdown 格式，包含详细的工作流指导和决策逻辑。例如 `/video` 命令包含：
- 项目状态检测逻辑
- 模板选择流程
- 品牌配置读取
- 项目创建步骤

---

## 五、Python Tools 层

`tools/` 目录包含 **18 个 Python 脚本**，是整个系统的执行层。

### 5.1 核心抽象

#### cloud_gpu.py — 多云 GPU 统一调用层

```python
def call_cloud_endpoint(provider, payload, tool_name, ...):
    if provider == "runpod":
        return _call_runpod(...)  # 异步 submit + poll
    elif provider == "modal":
        return _call_modal(...)   # 同步 POST
```

**RunPod 模式**（异步 submit + poll）：
1. 提交任务 → 获取 job_id
2. 轮询状态 → IN_QUEUE / IN_PROGRESS / COMPLETED / FAILED
3. 队列超时 → 主动取消任务
4. 获取结果 → 下载输出文件

**Modal 模式**（同步 POST）：
1. 直接 POST 到 FastAPI 端点
2. 等待响应
3. 下载输出文件

**费用估算系统**（项目最大亮点）：

```python
_GPU_HOURLY_RATES = {
    "modal":  {"A10G": 1.10, "A100": 3.73, "H100": 8.10},
    "runpod": {"ADA_24": 0.44, "AMPERE_80": 1.64},
}

# 任务完成后自动计算
cost = _estimate_cost(provider, tool_name, elapsed)
progress.event("cost", f"Est. cost: ${cost:.4f} ({elapsed:.0f}s on {provider})")
```

**ProgressReporter 心跳机制**：

```python
class ProgressReporter:
    @contextmanager
    def heartbeat(self, stage="waiting", msg_template="..."):
        """长时间 GPU 任务的心跳，防止被 Claude Code 判定卡死"""
```

#### file_transfer.py — 三级上传降级策略

```python
def upload_to_storage(file_path, prefix):
    # 1. Cloudflare R2（免费、零出站费）
    url, key = upload_to_r2(file_path, prefix)
    if url: return url, key

    # 2. litterbox.catbox.moe（200MB，24h 保留）
    # 3. 0x0.st（512MB，30 天保留）
    for name, func in fallback_services:
        try:
            url = func(file_path)
            if url: return url, None
        except: continue
```

### 5.2 工具清单

| 工具 | 类别 | 功能 | 云 GPU |
|------|------|------|--------|
| `cloud_gpu.py` | 基础设施 | 多云 GPU 统一调用层 | - |
| `file_transfer.py` | 基础设施 | 文件上传/下载/R2 管理 | - |
| `config.py` | 基础设施 | 环境变量/品牌配置加载 | - |
| `flux2.py` | AI 生成 | FLUX.2 文生图/图编辑 | A10G |
| `image_edit.py` | AI 生成 | Qwen 图片编辑 | A100 |
| `ltx2.py` | AI 生成 | LTX-2 文生视频/图生视频 | A100-80GB |
| `qwen3_tts.py` | AI 语音 | Qwen3-TTS 语音合成 | A10G |
| `sadtalker.py` | AI 视频 | SadTalker 说话人头像 | A10G |
| `music_gen.py` | AI 音乐 | ACE-Step 音乐生成 | A10G |
| `upscale.py` | AI 增强 | Real-ESRGAN 超分辨率 | A10G |
| `dewatermark.py` | AI 处理 | ProPainter 去水印 | A10G |
| `voiceover.py` | 音频工具 | AI 旁白生成 | - |
| `music.py` | 音频工具 | ElevenLabs 背景音乐 | - |
| `sfx.py` | 音频工具 | ElevenLabs 音效 | - |
| `sync_timing.py` | 音频工具 | 语音与场景时长同步 | - |
| `redub.py` | 实用工具 | 重新配音 | - |
| `addmusic.py` | 实用工具 | 添加背景音乐到视频 | - |
| `chain_video.py` | 实用工具 | 链式视频片段拼接 | - |
| `verify_setup.py` | 实用工具 | 验证环境配置 | - |
| `notebooklm_brand.py` | 实用工具 | NotebookLM 品牌化 | - |

### 5.3 工具接口设计

每个 Python 工具遵循统一的接口约定：

```python
# 1. 命令行接口（argparse）
parser = argparse.ArgumentParser()
parser.add_argument("--setup", action="store_true")     # 初始化
parser.add_argument("--dry-run", action="store_true")   # 预览模式
parser.add_argument("--progress", default="human")      # human | json

# 2. 云 GPU 调用（统一通过 cloud_gpu.py）
result, elapsed = call_cloud_endpoint(
    provider=provider,
    payload={"operation": "generate", "prompt": "...", ...},
    tool_name="flux2",
)

# 3. 费用自动计算和输出
cost = _estimate_cost(provider, tool_name, elapsed)
print(f"Est. cost: ${cost:.4f}")
```

---

## 六、Docker / 云部署

### 6.1 双云平台架构

```
                    ┌─────────────┐
                    │  tools/*.py  │  Python 客户端
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │ cloud_gpu.py │  统一抽象层
                    └──┬───────┬──┘
                       │       │
              ┌────────┴──┐ ┌──┴────────┐
              │   Modal    │ │  RunPod    │
              │ (推荐)     │ │  (备选)    │
              │            │ │            │
              │ $30/月免费  │ │ 按量付费   │
              │ 同步 POST   │ │ 异步 Poll  │
              └────────────┘ └────────────┘
```

### 6.2 部署配置对比

| 维度 | Modal | RunPod |
|------|-------|--------|
| **定义方式** | Python 声明式（`app.py`） | Dockerfile + `handler.py` |
| **入口协议** | `@modal.fastapi_endpoint` | `runpod.serverless.start` |
| **请求格式** | 直接 JSON | 包裹在 `{"input": {...}}` |
| **调用方式** | 同步 POST | 异步 submit + 轮询 |
| **冷启动** | 较快（镜像缓存） | 较慢（Docker pull） |
| **免费额度** | **$30/月** | 无 |
| **GPU 选择** | 声明式 `gpu="A10G"` | GraphQL API 选择 |
| **模型缓存** | 烘焙进镜像 | Dockerfile RUN 指令 |
| **Secret 管理** | `modal.Secret.from_name()` | 环境变量 |
| **并发控制** | `@modal.concurrent(max_inputs=1)` | `workersMax=1` |

### 6.3 模型权重烘焙策略

所有 Docker 镜像在构建时预下载模型权重，将冷启动从 5-10 分钟缩短到 30-90 秒：

**Modal 方式**：
```python
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch==2.5.1", ...)
    # 烘焙模型权重
    .run_commands(
        'python -c "'
        "from huggingface_hub import snapshot_download; "
        f"snapshot_download('{MODEL_ID}')"
        '"'
    )
)
```

**RunPod 方式**：
```dockerfile
# 模型权重烘焙到镜像
RUN python3 -c "from huggingface_hub import snapshot_download; \
    snapshot_download('Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice', ...)"
```

### 6.4 Modal 容器配置模式

```python
@app.cls(
    image=image,
    gpu="A10G",              # GPU 类型
    timeout=300,              # 函数超时 5 分钟
    scaledown_window=60,      # 60s 无请求自动缩容到零
)
@modal.concurrent(max_inputs=1)  # 并发限制
class Qwen3TTS:
    @modal.enter()
    def load_models(self):
        """容器启动时加载模型（执行一次）"""
        self.model = Qwen3TTSModel.from_pretrained(...)

    @modal.fastapi_endpoint(method="POST")
    def generate(self, request):
        """HTTP 端点"""
        ...
```

### 6.5 RunPod 端点资源配置

```python
{
    "name": ENDPOINT_NAME,
    "gpuIds": gpu_id,
    "workersMin": 0,       # 空闲时零 worker，不花钱
    "workersMax": 1,       # 最多 1 个 worker
    "idleTimeout": 5,      # 5 分钟空闲自动关闭
    "scalerType": "QUEUE_DELAY",
    "scalerValue": 4,
}
```

**关键控制**：
- `workersMin=0`：无任务时完全不产生 GPU 费用
- `workersMax=1`：限制并发，防止费用失控
- `idleTimeout=5`：5 分钟空闲即自动关闭

### 6.6 Docker 部署清单

| 模型 | Modal GPU | RunPod GPU | 镜像大小 |
|------|-----------|-----------|---------|
| FLUX.2 Klein 4B（文生图） | A10G | ADA_24 (16GB) | ~15GB |
| Qwen-Image-Edit（图片编辑） | A100 | AMPERE_80 (48GB) | ~20GB |
| LTX-2.3 22B（视频生成） | A100-80GB | - | ~25GB |
| Qwen3-TTS（语音合成） | A10G | 24GB | ~5GB |
| ACE-Step 1.5（音乐生成） | A10G | 16-24GB | ~10GB |
| SadTalker（说话人头像） | A10G | 24GB | ~8GB |
| Real-ESRGAN（超分辨率） | A10G | 24GB | ~5GB |
| ProPainter（去水印） | A10G | 24GB | ~10GB |

---

## 七、模板系统

### 7.1 模板概览

| 模板 | 用途 | 场景类型 | 复杂度 |
|------|------|---------|--------|
| **sprint-review** | Sprint 回顾 V1 | 4 种（title/overview/summary/credits） | 简单 |
| **sprint-review-v2** | Sprint 回顾 V2 | 12 种（可组合故事线） | 复杂（推荐） |
| **product-demo** | 产品/营销演示 | 6 种（title/problem/solution/demo/stats/cta） | 中等 |

### 7.2 Sprint Review V2（最完善的模板）

**12 种场景类型**（TypeScript 可辨识联合）：

```typescript
export type SceneConfig =
  | TitleScene        // 标题页
  | ContextScene      // 背景上下文
  | GoalScene         // 目标说明
  | HighlightsScene   // 亮点展示
  | DemoScene         // Demo 演示
  | CarryoverScene    // 延续事项
  | DecisionsScene    // 决策记录
  | MetricsScene      // 指标数据
  | LearningsScene    // 经验教训
  | RoadmapScene      // 路线图
  | SummaryScene      // 总结
  | CreditsScene;     // 片尾字幕
```

**建议叙事弧线**：

```
ACT 1: SET THE STAGE     → title, context, goal
ACT 2: THE JOURNEY       → highlights, demos, decisions
ACT 3: THE OUTCOME       → metrics, carryover, learnings
ACT 4: WHAT'S NEXT       → roadmap
CLOSING                   → summary, credits
```

**智能转场匹配**：

```typescript
function getDefaultPreset(_prev: SceneType, next: SceneType): TransitionPreset {
  switch (next) {
    case 'demo':     return 'slide';            // Demo 用滑动
    case 'summary':  return 'light-leak-warm';  // 总结用暖光
    case 'metrics':  return 'zoom-blur';        // 数据用缩放模糊
    case 'roadmap':  return 'light-leak-cool';  // 路线图用冷光
    // ...
  }
}
```

### 7.3 模板目录约定

每个模板包含：

```
templates/sprint-review-v2/
├── CLAUDE.md          # 模板使用指南（Claude Code 读取）
├── README.md          # 人类可读说明
├── package.json       # Remotion 依赖
├── remotion.config.ts # Remotion 配置
├── src/
│   ├── index.ts       # 入口
│   ├── Root.tsx       # 根组件（注册合成）
│   ├── SprintReview.tsx  # 主组件
│   ├── components/
│   │   ├── slides/    # 各场景组件
│   │   ├── core/      # 核心布局组件
│   │   └── demos/     # Demo 相关组件
│   └── config/
│       ├── types.ts       # 类型定义
│       ├── brand.ts       # 品牌（自动生成）
│       ├── theme.ts       # 主题
│       ├── transitions.ts # 转场配置
│       └── sprint-config.ts # 内容配置
└── tsconfig.json
```

### 7.4 模板参数化

模板通过 **config 对象** 驱动内容，不硬编码：

```typescript
// sprint-config.ts — 用户只需修改这个文件
export const sprintConfig: SprintReviewConfig = {
  sprint: { number: 42, dates: 'Dec 9-20', team: 'Mobile' },
  scenes: [
    { type: 'title', durationSeconds: 6, ... },
    { type: 'highlights', durationSeconds: 12, content: {
        highlights: ['Feature A', 'Feature B'],
    }},
    { type: 'demo', durationSeconds: 20, visual: {
        type: 'playwright', videoFile: 'demos/dark-mode.mp4',
    }},
  ],
};
```

---

## 八、品牌系统

### 8.1 品牌配置结构

```
brands/
├── default/               # 默认品牌
│   ├── brand.json         # 视觉配置
│   └── voice.json         # 语音配置
└── digital-samba/         # Digital Samba 品牌
    ├── brand.json
    ├── voice.json
    └── assets/
        └── ds-logo.png
```

### 8.2 brand.json 完整配置

```json
{
  "name": "Digital Samba",
  "colors": {
    "primary": "#ea580c",        "primaryLight": "#fb923c",
    "primaryDark": "#c2410c",    "accent": "#3771e0",
    "textDark": "#1e293b",       "textMedium": "#334155",
    "textLight": "#64748b",      "bgLight": "#ffffff",
    "bgDark": "#1a1a2e",         "bgOverlay": "rgba(255, 255, 255, 0.95)",
    "divider": "#e2e8f0",        "shadow": "rgba(0, 0, 0, 0.12)"
  },
  "fonts": {
    "primary": "Inter, system-ui, ...",
    "mono": "JetBrains Mono, ..."
  },
  "spacing": { "xs": 8, "sm": 16, "md": 24, "lg": 48, "xl": 80, "xxl": 120 },
  "borderRadius": { "sm": 6, "md": 10, "lg": 16 },
  "typography": {
    "h1": { "size": 88, "weight": 700 },
    "h2": { "size": 72, "weight": 700 },
    "h3": { "size": 48, "weight": 700 },
    "body": { "size": 44, "weight": 400 },
    "label": { "size": 34, "weight": 600, "letterSpacing": 2 }
  },
  "assets": { "logo": "assets/ds-logo.png" }
}
```

### 8.3 voice.json（双 TTS 引擎支持）

```json
{
  "voiceId": "YOUR_VOICE_ID_HERE",
  "settings": { "stability": 0.75, "similarityBoost": 0.9, "style": 0.15 },
  "model": "eleven_multilingual_v2",
  "qwen3": {
    "speaker": "Ryan",
    "language": "Auto",
    "tone": "",
    "instruct": "",
    "clone": null
  }
}
```

### 8.4 品牌加载链路

```
brand.json → lib/brand.ts (loadBrand())
                     │
                     ├──→ Theme → ThemeProvider → React 组件
                     │
                     └──→ tools/config.py (load_brand_voice_config()) → 音频工具
```

`/video` 命令创建项目时，自动将 `brand.json` 转换为 `src/config/brand.ts`：

```typescript
// 自动生成，不需要手动编辑
export const brand = {
  colors: { primary: '#ea580c', ... },
  fonts: { primary: fontFamily, ... },
};
export const brandTheme: Theme = { ... };
```

---

## 九、共享组件库

### 9.1 React 组件

| 组件 | 用途 |
|------|------|
| `AnimatedBackground` | 动画背景（4 种变体） |
| `Vignette` | 暗角效果 |
| `FilmGrain` | 胶片颗粒效果 |
| `LogoWatermark` | 品牌水印 |
| `NarratorPiP` | 画中画解说员 |
| `SplitScreen` | 分屏布局 |
| `MazeDecoration` | 等距网格装饰 |
| `SlideTransition` | 幻灯片转场 |
| `Label` | 标签组件 |
| `Envelope` | 信封动画 |
| `PointingHand` | 指向手势动画 |

### 9.2 转场效果库

7 个自定义转场 + 4 个官方转场重导出：

| 转场 | 效果 | 适用场景 |
|------|------|---------|
| `glitch` | 数字故障 + RGB 分离 | 科技 Demo、赛博朋克 |
| `rgbSplit` | 色差偏移 | 现代科技、活力场景 |
| `zoomBlur` | 径向运动模糊 | CTA、高能时刻 |
| `lightLeak` | 电影级镜头光晕 | 情感场景、庆祝 |
| `clockWipe` | 时钟式径向擦除 | 时间相关内容 |
| `pixelate` | 像素化溶解 | 复古/游戏 |
| `checkerboard` | 网格揭示（9 种图案） | 活力、结构化 |
| `slide` | 方向滑动（官方） | 通用 |
| `fade` | 淡入淡出（官方） | 通用 |
| `wipe` | 边缘擦除（官方） | 通用 |
| `flip` | 3D 翻转（官方） | 通用 |

每个转场都支持参数化配置：

```tsx
glitch({ intensity: 0.8, slices: 8, rgbShift: true })
lightLeak({ temperature: 'warm', direction: 'right', intensity: 0.8 })
checkerboard({ gridSize: 8, pattern: 'spiral', squareAnimation: 'scale' })
```

### 9.3 主题系统

```typescript
// ThemeProvider - React Context 注入
<ThemeProvider theme={brandTheme}>
  <SprintReview />
</ThemeProvider>

// useTheme Hook - 组件中获取主题
const theme = useTheme();
<div style={{ color: theme.colors.primary, fontSize: theme.typography.h1.size }}>
```

---

## 十、风控机制

### 10.1 费用控制系统

| 机制 | 实现 |
|------|------|
| GPU 费用实时估算 | 每次任务完成后自动计算并输出 `$X.XXXX` |
| 任务前费用预估 | 提交前预估处理时间和 GPU 费用 |
| Dry Run 模式 | `--dry-run` 不调用 API 即可预览操作 |
| 空闲自动关闭 | Modal 60s / RunPod 5min 无请求自动缩容 |
| Worker 数量限制 | `workersMax=1` 防止并发费用失控 |

### 10.2 多层超时控制

| 层级 | 时长 | 说明 |
|------|------|------|
| 全局超时 | 600s (10min) | `call_cloud_endpoint` 默认 |
| 队列超时 | 300s (5min) | 超时主动取消任务 |
| HTTP 请求 | 30s | 每次请求 |
| 工具级超时 | 动态计算 | 根据音频时长 × 倍率 + 缓冲 |
| 函数级超时 | 300s | Modal 容器 |

### 10.3 文件上传三级降级

```
R2（免费）→ litterbox（200MB，24h）→ 0x0.st（512MB，30天）
```

### 10.4 分层错误处理

```
RunPod: FAILED / CANCELLED / TIMED_OUT / 队列超时 → 主动取消
Modal: 422 / 408 / 503 → 对应错误提示
通用: Timeout / RequestException / Exception → 兜底处理
```

### 10.5 ProgressReporter 心跳

长时间 GPU 任务期间，每 15 秒发送心跳事件，防止 Claude Code 判定进程卡死。

---

## 十一、可借鉴的设计模式

### 11.1 Skill + Command + Tool 三层分离

```
Skill（知识层）：告诉 Claude Code "怎么做"
    ↓
Command（交互层）：引导用户完成工作流
    ↓
Tool（执行层）：实际执行操作
```

**优势**：各层独立迭代，Skill 可以不修改 Tool 就更新知识，反之亦然。

### 11.2 多云抽象 + 统一接口

```python
# cloud_gpu.py 统一了 Modal 和 RunPod 的差异
call_cloud_endpoint(provider, payload, tool_name)
```

**可借鉴点**：任何需要多云/多服务集成的 Skill 都可以采用这种抽象层模式。

### 11.3 品牌与模板分离

```
brands/     → 定义"长什么样"（颜色、字体、排版）
templates/  → 定义"说什么"（场景结构、叙事弧线）
/video      → 将两者绑定到具体项目
```

**可借鉴点**：任何需要主题化的 Skill 都可以采用这种配置分离模式。

### 11.4 模型权重烘焙

将 AI 模型权重在 Docker 构建时下载到镜像中：
- Modal：`.run_commands(python -c "snapshot_download(...)")`
- RunPod：`RUN python3 -c "snapshot_download(...)"`

**效果**：冷启动从 5-10 分钟降至 30-90 秒。

### 11.5 项目生命周期状态机

```typescript
type ProjectPhase = 'planning' | 'assets' | 'audio' | 'editing' | 'rendering' | 'complete';
```

通过 `project.json` 跟踪状态，支持跨 Claude Code 会话续作。

### 11.6 内部文件注册表

`_internal/toolkit-registry.json` 记录了所有 Skills、Commands、Tools 的元数据：

```json
{
  "name": "claude-code-video-toolkit",
  "version": "0.14.1",
  "skills": { "remotion": { "path": "...", "status": "stable" } },
  "commands": { "video": { "path": "...", "status": "stable" } },
  "tools": { "flux2": { "path": "...", "status": "stable" } }
}
```

**可借鉴点**：大型 Skill 项目都应该有类似的注册表机制。

### 11.7 环境变量模板

`.env.example` 提供完整的环境变量清单和注释：

```bash
# Cloudflare R2（文件传输）
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=

# Modal（推荐云 GPU）
MODAL_FLUX2_ENDPOINT_URL=
MODAL_QWEN3_TTS_ENDPOINT_URL=

# RunPod（备选云 GPU）
RUNPOD_API_KEY=
RUNPOD_FLUX2_ENDPOINT_ID=

# AI 语音
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
```

---

## 十二、参考链接

| 资源 | 链接 |
|------|------|
| GitHub 仓库 | https://github.com/digitalsamba/claude-code-video-toolkit |
| Demo 视频 | https://demos.digitalsamba.com/ |
| Remotion 官方 | https://www.remotion.dev/ |
| Modal 云平台 | https://modal.com/ |
| RunPod 云平台 | https://www.runpod.io/ |
| Context7 集成 | https://context7.com/digitalsamba/claude-code-video-toolkit |

---

> 本文档基于 2026-04-06 的 GitHub 仓库快照分析，项目版本 v0.14.1。
