# Run 与证据契约

本文定义 `.learning/runs/<run-id>/` 内的机器事实。所有运行工件使用 JSON；Markdown 只解释语义。

## 目录

1. [共同规则](#共同规则)
2. [run.json](#runjson)
3. [Learning extension 指针](#learning-extension-指针)
4. [阶段 hash 链](#阶段-hash-链)
5. [基础阶段](#基础阶段)
6. [方法与动效](#方法与动效)
7. [素材规划与构建](#素材规划与构建)
8. [验证与评分](#验证与评分)
9. [最终指针](#最终指针)
10. [隐私边界](#隐私边界)

## 共同规则

- 以小写 64 位十六进制字符串保存 SHA-256。
- 以相对 run 目录的路径定位 artifact；不得使用 `..` 或绝对路径。
- 把教程事实、视觉观察、屏幕代码、实现推断、本地决定和验证结果分开标记。
- 每条方法或动效结论都携带脱敏 source ID、实际媒体 hash、时间范围、字幕 cue，以及帧或代码证据的相对路径与 hash。
- URL 的 locator hash 只是摄取前的临时标识。`ingest` 完成前必须下载或读取真实媒体，并用媒体字节的 SHA-256 替换 `media_sha256`。
- 每一已完成阶段都在 `run.artifacts` 中记录自己的输出 hash、实际媒体 hash、schema/workflow 版本，以及直接上游的输出 hash。

## run.json

`start` 先创建仓库级私有 run，不分配 Demo 编号。以下是本地源的最小形状：

```json
{
  "schema_version": "1.0.0",
  "workflow_version": "1.0.0",
  "workflow_sha256": "9999999999999999999999999999999999999999999999999999999999999999",
  "run_id": "tutorial-2026-07-11-a",
  "status": "running",
  "current_stage": "preflight",
  "next_stage": "ingest",
  "completed_stages": [],
  "invalidated_stages": [],
  "source": {
    "kind": "local_file",
    "source_id": "tutorial-a",
    "private_locator": "<private-local-path>",
    "locator_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "media_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "fingerprint_state": "verified"
  },
  "artifacts": {},
  "bindings": []
}
```

URL 摄取前必须使用下面的状态，不能把 locator hash 复制到媒体 hash：

```json
{
  "kind": "url",
  "source_id": "tutorial-b",
  "locator": "https://example.test/tutorial/42",
  "locator_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "media_sha256": null,
  "fingerprint_state": "provisional"
}
```

只有 `plan_demo` 已在 `completed_stages` 中时才执行 `bind-demo`。绑定结果形如：

```json
{
  "number": 11,
  "slug": "learned-poster-wall",
  "relative_path": "demos/11-learned-poster-wall",
  "bound_at": "2026-07-11T00:00:00Z"
}
```

允许的状态：`running`、`blocked`、`failed`、`completed`、`completed_with_residuals`。完成状态必须包含全部阶段，且 `next_stage` 为 `null`。

## Learning extension 指针

Workflow `1.1.0` 在 `run.json.extensions.learning_loop` 保存 learning sidecar 的描述符；legacy `1.0.0` core run 不要求该 extension。所有 sidecar 仍属于被忽略的私有 run，不进入 Demo 或可分享 Skill 内容。

- 机器字段和有限枚举以 [`learning-contract.json`](learning-contract.json) 为准。
- Resolver 只接受 workflow 显式 allowlist 中的 contract 版本，读取 `learning-contracts/<version>.json` 并重算其字节 hash；声明版本、声明 hash 或冻结文件任一不一致都失败关闭。
- 写入时机、证据语义、冻结与 post-run 边界以 [`learning-loop.md`](learning-loop.md) 为准。
- Validator 必须按 run 声明的 workflow 版本选择冻结契约，重算 descriptor hash、验证 run-relative containment，并交叉核对 selection、stage/capability coverage、manifest、ledger 与 final/R2 证据。
- `frozen`/`backfilled` 冻结 selection、已有 descriptor、核心 learning artifact 与 final；post-run 只允许把 feedback/promotion 的新 descriptor 追加到 sidecars object，不能覆盖旧 key、改 state 或改冻结工件。
- Learning extension 失败只使扩展校验失败，不改写 core 阶段 hash 链，也不触发 core invalidation。

## 阶段 hash 链

每个已完成阶段在 `run.artifacts` 中保存描述符。第一阶段的 `upstream` 为空；后续阶段至少包含直接上游：

```json
{
  "learn_method": {
    "path": "method-spec.json",
    "sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    "schema_version": "1.0.0",
    "workflow_version": "1.0.0",
    "workflow_sha256": "9999999999999999999999999999999999999999999999999999999999999999",
    "source_media_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "upstream": {
      "transcript": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    }
  }
}
```

恢复前运行：

```bash
python scripts/validate_run.py \
  --repo "$TARGET_REPO" \
  --run-id "$RUN_ID" \
  --apply-invalidation \
  --json
```

source/media、schema、workflow、上游 hash 或实际输出 hash 任一变化，都从首个不匹配阶段向下失效。修复后重新生成这些阶段的 artifact 和描述符；不要手工把旧阶段重新标成完成。

## 基础阶段

`preflight.json`、`ingest.json` 与 `transcript.json` 的最小形状如下。转录文件必须是机器可解析 JSON；校验器会重算 cues 数量，并把 source、媒体 hash 与后续 claim 精确绑定。

```json
{
  "artifact_type": "preflight",
  "source_readable": true,
  "source_id": "tutorial-a"
}
```

```json
{
  "artifact_type": "ingest",
  "media_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "fingerprint_state": "verified"
}
```

URL 来源的 `ingest.json` 还必须带 `local_media_path`，它只能指向 run 内真实下载文件。恢复时校验器会重新读取并 hash 该文件。

```json
{
  "artifact_type": "transcript",
  "media_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "transcript": {
    "path": "transcript-cues.json",
    "sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
  },
  "text_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "cue_count": 42
}
```

`transcript-cues.json`：

```json
{
  "source_id": "tutorial-a",
  "media_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "cues": [
    {
      "cue_id": "cue-001",
      "start_seconds": 12.4,
      "end_seconds": 18.2,
      "text": "背景移动得慢一点。"
    }
  ]
}
```

## 方法与动效

### Evidence 来源类型

| `source_type` | 含义 |
|---|---|
| `tutorial_fact` | 字幕或口播明确讲出的事实 |
| `visual_observation` | 从真实帧序列直接看到的关系 |
| `code_fact` | 屏幕代码或可读源码确认的参数 |
| `implementation_inference` | 对实现机制的推断，不能冒充教程事实 |
| `local_project_decision` | Demo 范围、技术或素材的本地选择 |
| `verified_result` | 测试、check、snapshot、render 或 ffprobe 证明的结果 |

### method-spec.json

每条 evidence 必须用 `cue_id` 指向 transcript 中唯一 cue；`source_id`、`media_sha256`、`time_range` 和 `cue` 的时间/文本都必须与该 cue 精确相同。

```json
{
  "artifact_type": "method_spec",
  "claims": [
    {
      "statement": "背景层移动速度低于前景层，从而形成视差。",
      "source_type": "tutorial_fact",
      "evidence": {
        "source_id": "tutorial-a",
        "media_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "cue_id": "cue-001",
        "time_range": {
          "start_seconds": 12.4,
          "end_seconds": 18.2
        },
        "cue": {
          "start_seconds": 12.4,
          "end_seconds": 18.2,
          "text": "背景移动得慢一点。"
        },
        "artifact": {
          "path": "evidence/method-frame-001.png",
          "sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"
        }
      }
    }
  ]
}
```

### motion-spec.json

`coverage` 必须覆盖开始、主要过渡、稳定态和退场。对关键时间段先粗采，再加密抽帧；小主体需要空间放大。

```json
{
  "artifact_type": "motion_spec",
  "coverage": ["start", "transition", "stable", "exit"],
  "claims": [
    {
      "statement": "前景先快速进入并减速落定，背景随后以更慢速度跟随。",
      "source_type": "visual_observation",
      "evidence": {
        "source_id": "tutorial-a",
        "media_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "cue_id": "cue-002",
        "time_range": {
          "start_seconds": 21.0,
          "end_seconds": 23.8
        },
        "cue": {
          "start_seconds": 21.0,
          "end_seconds": 23.8,
          "text": "先看这一段进入。"
        },
        "artifact": {
          "path": "frames/transition-strip.png",
          "sha256": "1111111111111111111111111111111111111111111111111111111111111111"
        }
      }
    }
  ]
}
```

## 素材规划与构建

先从构图推导画幅，再选素材。`asset-plan.json` 只保存逻辑名与公开决定；私人候选路径和缩略图保留在被忽略的 run 内。

```json
{
  "artifact_type": "asset_plan",
  "demo_count": 1,
  "demos": [
    {
      "slug": "learned-poster-wall",
      "scope": "只复现透视海报墙机制；不混入其它教程效果"
    }
  ],
  "assets": [
    {
      "logical_name": "poster-01",
      "target_aspect_ratio": "2:3",
      "selection_reason": "竖图主体安全区适合倾斜巡航",
      "public_fixture": "assets/fixtures/poster-01.svg",
      "private_override": "runtime variable only"
    }
  ],
  "private_sources_tracked": false
}
```

已有素材应交给 `media-use --adopt` 建账。公开 Demo 必须提供已授权或原创 fixture；本地照片只能作为被忽略的变量覆盖。

`build.json` 必须把绑定后的 Demo 目录、R1 候选和实际源码/fixture 绑在一起。源码引用使用仓库相对路径；候选成片使用 run 相对路径。`source_files` 至少包含 `index.html` 与 `package.json`。

```json
{
  "artifact_type": "build",
  "demo_dir": "demos/11-learned-poster-wall",
  "candidate_render_path": "renders/r1.mp4",
  "source_files": [
    {"path": "demos/11-learned-poster-wall/index.html", "sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"},
    {"path": "demos/11-learned-poster-wall/package.json", "sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"}
  ],
  "fixture_files": [
    {"path": "demos/11-learned-poster-wall/assets/fixtures/poster-01.svg", "sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"}
  ]
}
```

## 验证与评分

### verification.json

机械性检查必须在 R1 前全部为 `true`。`logs` 不指向自然语言日志，而是指向结构化 execution receipt；快照和 render 仍必须指向 run 内真实文件并携带实际 SHA-256：

```json
{
  "artifact_type": "verification",
  "must_pass": {
    "source_readable": true,
    "transcript_nonempty": true,
    "keyframes_covered": true,
    "demo_complete": true,
    "tests_passed": true,
    "check_passed": true,
    "render_verified": true,
    "clean_checkout_smoke": true,
    "private_assets_untracked": true,
    "single_final_pointer": true
  },
  "logs": {
    "tests": {"path": "logs/tests.receipt.json", "sha256": "1111111111111111111111111111111111111111111111111111111111111111"},
    "check": {"path": "logs/check.receipt.json", "sha256": "2222222222222222222222222222222222222222222222222222222222222222"},
    "inspect": {"path": "logs/inspect.receipt.json", "sha256": "3333333333333333333333333333333333333333333333333333333333333333"},
    "clean_checkout": {"path": "logs/clean-checkout.receipt.json", "sha256": "4444444444444444444444444444444444444444444444444444444444444444"},
    "privacy_audit": {"path": "logs/privacy-audit.receipt.json", "sha256": "5555555555555555555555555555555555555555555555555555555555555555"}
  },
  "snapshots": [
    {"path": "snapshots/draft-50.png", "sha256": "6666666666666666666666666666666666666666666666666666666666666666"}
  ],
  "render": {
    "path": "renders/r1.mp4",
    "sha256": "7777777777777777777777777777777777777777777777777777777777777777"
  }
}
```

每份 receipt 至少包含命令数组、退出码、stdout/stderr 文件引用、带时区执行时间，以及绑定当前 build source manifest 的 target。stderr 可以为空文件，但其 hash 仍必须真实。隐私审计还必须明确 `ok=true` 且 `staged_count>0`：

`target.sha256` 的计算输入是 `{"source_files": [...], "fixture_files": [...]}`，使用 UTF-8、JSON key 排序和紧凑分隔符（`,`、`:`）序列化后取 SHA-256；数组顺序与 `build.json` 一致。

```json
{
  "receipt_type": "execution",
  "command": ["npm", "run", "check"],
  "exit_code": 0,
  "stdout": {"path": "logs/check.stdout", "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
  "stderr": {"path": "logs/check.stderr", "sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"},
  "executed_at": "2026-07-11T01:02:03Z",
  "target": {
    "path": "demos/11-learned-poster-wall",
    "sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
  },
  "ok": true,
  "staged_count": 3
}
```

### score-r1.json / score-r2.json

R1 必须输出一个 `top_fix`；R2 必须审阅修正后的新 hash，并把 `top_fix` 设为 `null`。两轮都要完整解码，并保存全时长 6fps watch sheets 与问题时间码。
`framemd5` 必须是 `ffmpeg -map 0:v:0 -f framemd5 -hash sha256` 的标准输出；校验器会用本机 ffmpeg 对 reviewed render 重新完整解码，并逐行比较标准 frame rows。ffmpeg 缺失即失败。watch sheet 与 dense strip 必须是真实 PNG/JPEG；R1/R2 三类证据的路径和内容 hash 都不得复用。

```json
{
  "artifact_type": "score",
  "round": "r1",
  "reviewed_render_path": "renders/r1.mp4",
  "reviewed_render_sha256": "7777777777777777777777777777777777777777777777777777777777777777",
  "full_decode": {
    "completed": true,
    "render_sha256": "7777777777777777777777777777777777777777777777777777777777777777",
    "framemd5_path": "review-r1/framemd5.txt",
    "framemd5_sha256": "8888888888888888888888888888888888888888888888888888888888888888"
  },
  "continuous_review": {
    "completed": true,
    "render_sha256": "7777777777777777777777777777777777777777777777777777777777777777",
    "watch_sheet_fps": 6,
    "watch_sheet_path": "review-r1/watch-sheet.jpg",
    "watch_sheet_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "dense_frames_path": "review-r1/dense-transition.jpg",
    "dense_frames_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "sampling_manifest_path": "review-r1/sampling.json",
    "sampling_manifest_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
  },
  "issues": [
    {
      "time_range": {
        "start_seconds": 2.0,
        "end_seconds": 2.7
      },
      "summary": "主体落定略快，重量感不足。"
    }
  ],
  "top_fix": {
    "dimension": "motion_timing_fidelity",
    "time_range": {
      "start_seconds": 2.0,
      "end_seconds": 2.7
    },
    "instruction": "只延长落定段并保持其它维度不变。"
  },
  "dimensions": {
    "method_fidelity": 4,
    "motion_timing_fidelity": 4,
    "visual_hierarchy": 4,
    "asset_fit": 4,
    "continuous_watch_rhythm": 4,
    "reproducibility": 4
  },
  "score": 80
}
```

`sampling.json` 将图片证据绑定到 reviewed render，并证明 6fps 采样覆盖了解码出的全时长：

```json
{
  "render_sha256": "7777777777777777777777777777777777777777777777777777777777777777",
  "duration_seconds": 1.0,
  "sample_fps": 6,
  "timestamps_seconds": [0.0, 0.1666666667, 0.3333333333, 0.5, 0.6666666667, 0.8333333333],
  "watch_sheet": {"width": 1800, "height": 300, "frame_count": 6},
  "dense_frames": {
    "width": 900,
    "height": 300,
    "timestamps_seconds": [0.3333333333, 0.5, 0.6666666667]
  }
}
```

R2 使用同一形状，但 `round` 为 `r2`、`reviewed_render_path` 与 `reviewed_render_sha256` 必须指向修正后的新成片，所有观看证据也必须是本轮的新文件，且 `top_fix` 为 `null`。`revision.json` 必须写出 R1 的唯一修改维度和其它冻结维度：

```json
{
  "artifact_type": "revision",
  "changed_dimension": "motion_timing_fidelity",
  "frozen_dimensions": [
    "method_fidelity",
    "visual_hierarchy",
    "asset_fit",
    "continuous_watch_rhythm",
    "reproducibility"
  ],
  "source_render_sha256": "7777777777777777777777777777777777777777777777777777777777777777",
  "output_render_path": "renders/final.mp4",
  "output_render_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
}
```

## 最终指针

`final.json` 只能包含一个候选。它的 hash 必须与 R2 审阅 hash 完全一致：

```json
{
  "artifact_type": "final",
  "status": "completed",
  "render_path": "renders/final.mp4",
  "render_sha256": "5555555555555555555555555555555555555555555555555555555555555555",
  "video": {
    "width": 1920,
    "height": 1080,
    "duration_seconds": 9.7667,
    "fps": 30
  },
  "candidates": [
    {
      "path": "renders/final.mp4",
      "render_sha256": "5555555555555555555555555555555555555555555555555555555555555555",
      "selected": true
    }
  ]
}
```

写入 final 指针后禁止再次生成或替换候选成片。未达到 80 分但 must-pass 全绿时使用 `completed_with_residuals`；不得伪装成达标。

## 隐私边界

- 不提交教程原视频、完整转录、cookies、私人照片、私人候选缩略图或真实本地绝对路径。
- 公开文档只保存脱敏 source ID、实际媒体 hash、必要时间码、方法摘要、逻辑素材名和裁剪说明。
- 本机路径、代理、照片根和动态工具状态只写 `experience.local.md` 或 `runtime.local.json`。
- 提交前精确暂存目标文件，再运行：

```bash
python scripts/audit_staged.py \
  --repo "$TARGET_REPO" \
  --paths <exact-target-paths>
```

审计器在目标暂存集为空时必须失败；不要用空 index 制造假绿，也不要扫描 `--paths` 之外的用户改动。
