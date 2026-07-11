---
name: subtitle-to-audio
description: "字幕/文字转语音工具。当用户需要将 SRT 字幕或纯文本文件转为语音音频（MP3/WAV/OGG）时触发。使用豆包大模型语音合成 API，支持多种音色和语速调节。"
---

<role>
你是文字转语音专家，擅长利用豆包大模型 TTS 服务将文本内容高质量地合成为自然流畅的语音音频。
</role>

<purpose>
当用户需要将 SRT 字幕文件或纯文本文件（TXT）转换为语音音频文件（MP3/WAV/OGG）时，提供一站式语音合成方案。使用火山引擎豆包大模型 TTS API，支持多种音色选择、语速调节和输出格式配置。
</purpose>

<trigger>
```
字幕转语音
文字转语音
文本朗读
把字幕转成音频
subtitle to audio
text to speech
TTS
语音合成
朗读字幕
SRT 转音频
```
</trigger>

<gsd:workflow>
  <gsd:meta>
    <name>subtitle-to-audio</name>
    <owner>video-processing</owner>
    <requires>python3, ffmpeg, requests, AskUserQuestion</requires>
    <checkpoints>
      <checkpoint order="1">环境依赖检查通过</checkpoint>
      <checkpoint order="2">输入文件存在且格式支持</checkpoint>
      <checkpoint order="3">用户选择音色和参数</checkpoint>
      <checkpoint order="4">豆包 TTS API 凭证验证通过</checkpoint>
      <checkpoint order="5">语音合成完成，音频文件生成</checkpoint>
    </checkpoints>
    <constraints>
      <constraint>音色选择不可默认、不可跳过，必须等用户明确选择</constraint>
      <constraint>云端 API 密钥不得硬编码，必须通过环境变量或配置文件读取</constraint>
      <constraint>与 audio-to-subtitle 共享豆包 API 凭证（~/.audio2subtitle/config.json）</constraint>
      <constraint>长文本（>10000 字符）自动分段合成再用 ffmpeg 拼接</constraint>
      <constraint>MacBook Air 无风扇，批量任务建议串行处理避免过热降频</constraint>
    </constraints>
  </gsd:meta>

  <gsd:goal>将用户指定的 SRT/TXT 文件合成为高质量语音音频文件，输出到指定目录。</gsd:goal>

  <!-- ==================== Phase 1: 环境检查 ==================== -->
  <gsd:phase name="precheck" order="1">
    <gsd:step>并行检查 Python3、ffmpeg 是否已安装</gsd:step>
    <gsd:step>检查豆包 API 凭证是否存在（~/.audio2subtitle/config.json 或环境变量 DOUBAO_APP_ID / DOUBAO_ACCESS_TOKEN）</gsd:step>
    <gsd:step>确认输入文件路径和格式（SRT 或 TXT）</gsd:step>
    <gsd:step>统计文本字符数，如 >10000 字符则提醒将自动分段合成</gsd:step>
    <gsd:checkpoint>环境依赖就绪，凭证验证通过，输入文件可访问</gsd:checkpoint>
  </gsd:phase>

  <!-- ==================== Phase 2: 参数配置（3 步顺序交互） ==================== -->
  <gsd:phase name="config" order="2">

    <!-- Step 1: 音色选择 -->
    <gsd:step>
      📝 【Step 1/3：选择音色 — 必须单独执行，不可合并】

      使用 AskUserQuestion 让用户选择发音人：

      推荐音色（按场景分类）：
      - BV001_streaming：通用女声（免费，12种情感，适合通用场景）
      - BV002_streaming：通用男声（免费，适合通用场景）
      - BV700_streaming：灿灿（免费，22种情感，支持5国语言）
      - BV123_streaming：阳光青年（7种情感）
      - BV120_streaming：反卷青年（7种情感）
      - BV406_streaming：梓梓（7种情感，超自然音色）
      - BV405_streaming：甜美小源（5种情感，智能助手风格）

      规则：
      - 此步骤不可跳过、不可默认选择
      - 必须等待用户明确选择后才进入下一步
      - 禁止在这一步同时询问语速、格式等其他问题
    </gsd:step>

    <!-- Step 2: 语速调节 -->
    <gsd:step>
      📝 【Step 2/3：语速和情感】

      使用 AskUserQuestion 选择语速：
      - 0（正常速度，默认）
      - 25（1.25x 略快）
      - 50（1.5x 较快）
      - -25（0.75x 略慢）
      - 自定义（-50 到 100）
    </gsd:step>

    <!-- Step 3: 输出格式 -->
    <gsd:step>
      📝 【Step 3/3：输出格式和目录】

      使用 AskUserQuestion 选择输出音频格式：
      - MP3（推荐，兼容性最好）
      - WAV（无损，体积较大）
      - OGG Opus（体积小，适合网络传输）

      确认输出目录（默认与输入文件同目录）
    </gsd:step>

    <gsd:checkpoint>用户已确认所有合成参数</gsd:checkpoint>
  </gsd:phase>

  <!-- ==================== Phase 3: 文本预处理 ==================== -->
  <gsd:phase name="preprocess" order="3">
    <gsd:step>根据输入格式解析文本：
      - SRT：提取纯文本（去除序号、时间戳、空行）
      - TXT：直接读取全部内容
    </gsd:step>
    <gsd:step>文本清理：去除多余空白、特殊标记</gsd:step>
    <gsd:step>长文本分段：如 >10000 字符，按句子边界分段，每段 <10000 字符</gsd:step>
    <gsd:step>报告分段情况（段数、每段字符数）</gsd:step>
    <gsd:checkpoint>文本已预处理完成，分段信息已确认</gsd:checkpoint>
  </gsd:phase>

  <!-- ==================== Phase 4: 语音合成 ==================== -->
  <gsd:phase name="synthesize" order="4">
    <gsd:step>展示参数确认表（音色 / 语速 / 格式 / 字符数 / 段数 / 输出路径）</gsd:step>
    <gsd:step>执行合成脚本（加 --yolo 跳过脚本内交互，因为 Claude 侧已完成交互确认）</gsd:step>

    <!-- 错误处理：豆包 TTS API 失败 -->
    <gsd:step>
      🛑 【豆包 TTS API 失败时 — Decision 检查点，禁止自动回退】

      当 TTS 合成失败时，按以下流程处理：

      1. ✅ 展示诊断报告（脚本已输出到 stderr）
      2. ✅ 解释错误原因：
         - 凭证未配置 → 说明需要获取 APP ID 和 Access Token
         - 认证失败 → 提示检查凭证是否正确
         - resource not granted → 说明火山引擎账号未开通 TTS 服务，提供控制台链接
         - 文本过长 → 提示分段处理
      3. 🔄 使用 AskUserQuestion 让用户选择下一步：
         - 选项 A：去开通服务，修复配置后重试
         - 选项 B：调整参数后重试
         - 选项 C：取消本次操作
      4. 根据用户选择执行

      绝对禁止的行为：
      - ❌ 未经用户同意自动重试
      - ❌ 在用户不知情的情况下修改参数
    </gsd:step>

    <gsd:step>处理完成后验证输出文件完整性</gsd:step>
    <gsd:checkpoint>语音合成完成，音频文件已生成</gsd:checkpoint>
  </gsd:phase>

  <!-- ==================== Phase 5: 输出交付 ==================== -->
  <gsd:phase name="deliver" order="5">
    <gsd:step>报告输出文件路径、大小和音频时长</gsd:step>
    <gsd:step>如有多段，报告拼接结果</gsd:step>
    <gsd:step>如质量不佳，建议调整音色或语速重新合成</gsd:step>
  </gsd:phase>
</gsd:workflow>

# Subtitle to Audio - 字幕/文字转语音工具

基于豆包大模型 TTS API 的文字转语音工具，将 SRT 字幕和纯文本转为自然流畅的语音音频。

## ⚠️ 用户交互点总结

| 阶段 | 标记 | 交互内容 | 检查点类型 |
|------|------|----------|------------|
| Phase 1 | ✅ | 环境检查结果 | auto-verify |
| Phase 1 | 🛑 | 配置豆包 API 凭证（凭证缺失时） | human-action |
| Phase 2 Step 1 | 📝 | 选择音色（7+ 种可选） | decision |
| Phase 2 Step 2 | 📝 | 选择语速 | decision |
| Phase 2 Step 3 | 📝 | 选择输出格式（MP3/WAV/OGG） | decision |
| Phase 3 | ✅ | 文本预处理和分段结果 | auto-verify |
| Phase 4 | 🔄 | TTS 失败时选择下一步（仅失败时） | decision |
| Phase 5 | ✅ | 验证输出结果 | auto-verify |

**LLM 执行提示**：
- 🛑 → **必须等待用户完成操作**（如配置 API 凭证），不能跳过
- 📝 → **需要用户输入**，使用 AskUserQuestion
- ✅ → **自动验证后报告结果**，不需要用户操作
- 🔄 → **需要用户选择**，提供选项，不能自动决定

## 核心架构

```
SRT/TXT 文件 → 文本解析 → 长文本分段 → 豆包 TTS API → 音频拼接 → MP3/WAV/OGG
                                                  ↕
                                          异步 submit/query 模式
```

## 环境要求

| 依赖 | 安装方式 | 说明 |
|------|----------|------|
| Python 3.10+ | `brew install python` | 运行时 |
| requests | `pip install requests` | HTTP 客户端 |
| ffmpeg | `brew install ffmpeg` | 音频拼接（长文本分段时） |

### 首次安装

```bash
pip install requests
brew install ffmpeg
```

## 支持格式

### 输入

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| SRT | `.srt` | 通用字幕格式（提取纯文本） |
| TXT | `.txt` | 纯文本文件 |

### 输出

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| MP3 | `.mp3` | 兼容性最好（默认） |
| WAV | `.wav` | 无损，体积较大 |
| OGG Opus | `.ogg` | 体积小，适合网络 |

## 豆包 TTS 服务

### 必须开通的服务

在火山引擎控制台开通：https://console.volcengine.com/speech/service/subscription

| 服务名称 | resource_id | 价格 | 说明 |
|---------|-------------|------|------|
| **豆包大模型语音合成** | `volc.service_type.10029` | 按量计费 | 大模型 TTS 1.0 音色 |

> 新用户有 2 万字符免费额度。
> 2.0 音色（更便宜）需使用 `seed-tts-2.0` resource_id。

### API 注册指南

1. 访问 https://www.volcengine.com 注册并实名认证
2. 进入 https://console.volcengine.com/speech/service/subscription
3. 开通「豆包大模型语音合成」服务
4. 进入 https://console.volcengine.com/speech/app 创建应用，获取 **APP ID** 和 **Access Token**
5. 确保应用已绑定到开通的服务
6. 配置凭证（三选一）：
   - 运行 `python3 scripts/synthesize.py --setup-doubao` 交互式输入
   - 写入 `~/.audio2subtitle/config.json`（与 audio-to-subtitle 共享）
   - 设置环境变量 `DOUBAO_APP_ID` + `DOUBAO_ACCESS_TOKEN`

> **注意**：与 audio-to-subtitle（音频转字幕）使用相同的 APP ID 和 Access Token，无需重复配置。

### 音色列表（常用）

| 音色名称 | voice_type | 情感支持 | 免费 | 说明 |
|----------|-----------|---------|------|------|
| 通用女声 | `BV001_streaming` | 12种 | ✅ | 通用场景首选 |
| 通用男声 | `BV002_streaming` | - | ✅ | 通用男声 |
| 灿灿 | `BV700_streaming` | 22种 | ✅ | 支持5国语言 |
| 阳光青年 | `BV123_streaming` | 7种 | - | 年轻男声 |
| 反卷青年 | `BV120_streaming` | 7种 | - | 个性男声 |
| 梓梓 | `BV406_streaming` | 7种 | - | 超自然音色 |
| 甜美小源 | `BV405_streaming` | 5种 | - | 智能助手风格 |

完整音色列表（1.0）：https://www.volcengine.com/docs/6561/97465

### 豆包语音合成 2.0 音色

> 2.0 音色价格更便宜（3 元/万字符 vs 1.0 的 5 元/万字符），支持情感变化、指令遵循、ASMR 等高级能力。

| 音色名称 | voice_type | 语种 | 支持能力 |
|----------|-----------|------|----------|
| Vivi 2.0 | `zh_female_vv_uranus_bigtts` | 中/日/印尼/墨西哥西班牙语 | 情感变化、指令遵循、ASMR |
| 甜美小源 2.0 | `zh_female_tianmeixiaoyuan_uranus_bigtts` | 中文 | 情感变化、指令遵循、ASMR |
| 知性灿灿 2.0 | `zh_female_cancan_uranus_bigtts` | 中文 | 情感变化、指令遵循、ASMR |
| 黑猫侦探社咪仔 2.0 | `zh_female_mizai_uranus_bigtts` | 中文 | 情感变化、指令遵循、ASMR |
| 爽快思思 2.0 | `zh_female_shuangkuaisisi_uranus_bigtts` | 中文 | 情感变化、指令遵循、ASMR |
| 清新女声 2.0 | `zh_female_qingxinnvsheng_uranus_bigtts` | 中文 | 情感变化、指令遵循、ASMR |
| 撒娇学妹 2.0 | `zh_female_sajiaoxuemei_uranus_bigtts` | 中文 | 情感变化、指令遵循、ASMR |
| 邻家女孩 2.0 | `zh_female_linjianvhai_uranus_bigtts` | 中文 | 情感变化、指令遵循、ASMR |
| 暖阳女声 2.0 | `zh_female_kefunvsheng_uranus_bigtts` | 中文 | 情感变化、指令遵循、ASMR |
| 流畅女声 2.0 | `zh_female_liuchangnv_uranus_bigtts` | 中文 | 情感变化、指令遵循、ASMR |
| 儿童绘本 2.0 | `zh_female_xiaoxue_uranus_bigtts` | 中文 | 情感变化、指令遵循、ASMR |
| 魅力苏菲 2.0 | `zh_male_sophie_uranus_bigtts` | 中文 | 情感变化、指令遵循、ASMR |
| 云舟 2.0 | `zh_male_m191_uranus_bigtts` | 中文 | 情感变化、指令遵循、ASMR |
| Stokie | `en_female_stokie_uranus_bigtts` | 美式英语 | 情感变化、指令遵循、ASMR |
| 天才同桌 | `saturn_zh_male_tiancaitongzhuo_tob` | 中文 | 指令遵循、COT/QA |
| 温婉珊珊 2.0 | `saturn_zh_female_wenwanshanshan_cs_tob` | 中文 | 指令遵循 |
| 轻盈朵朵 2.0 | `saturn_zh_female_qingyingduoduo_cs_tob` | 中文 | 指令遵循 |

完整 2.0 音色列表：https://www.volcengine.com/docs/6561/1263472

## 使用方式

### 交互模式（推荐）

```bash
# 直接运行，会先确认参数再执行
python3 scripts/synthesize.py subtitle.srt
python3 scripts/synthesize.py text.txt
```

### YOLO 模式（跳过交互）

```bash
# 跳过交互，使用默认参数
python3 scripts/synthesize.py subtitle.srt --yolo
```

### 单文件合成

```bash
python3 scripts/synthesize.py subtitle.srt -f wav
python3 scripts/synthesize.py subtitle.srt -s BV002_streaming
python3 scripts/synthesize.py subtitle.srt -r 25
python3 scripts/synthesize.py subtitle.srt -o ~/Desktop/audio/
```

### 命令选项

| 选项 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--format` | `-f` | mp3 | 输出格式 (mp3/wav/ogg) |
| `--output` | `-o` | 输入同目录 | 输出目录 |
| `--speaker` | `-s` | BV001_streaming | 发音人音色 |
| `--speed` | `-r` | 0 | 语速 [-50, 100]，0=正常 |
| `--sample-rate` | - | 24000 | 采样率 |
| `--yolo` | - | false | YOLO 模式：跳过交互 |
| `--show-config` | - | false | 查看当前配置 |
| `--setup-doubao` | - | false | 配置豆包 API 凭证 |

## 性能参考

| 文本长度 | 合成时间 | 音频时长 | 说明 |
|---------|---------|---------|------|
| 100 字 | ~5s | ~30s | 短文本 |
| 1000 字 | ~15s | ~5min | 中等文本 |
| 5000 字 | ~60s | ~25min | 长文本（单次） |
| 10000+ 字 | 分段处理 | - | 自动分段 + ffmpeg 拼接 |

<reference>
  <ref id="subtitle-to-audio-doc" path="SKILL.md" required="false">
    完整的 subtitle-to-audio 使用文档，包含环境要求、支持格式、TTS 服务说明和使用方式。
  </ref>
  <ref id="doubao-tts-api" url="https://www.volcengine.com/docs/6561/1167803" required="false">
    豆包语音合成 API 总文档。
  </ref>
  <ref id="doubao-tts-async" url="https://www.volcengine.com/docs/6561/1829010" required="false">
    豆包 TTS 异步长文本接口文档。
  </ref>
  <ref id="doubao-tts-streaming" url="https://www.volcengine.com/docs/6561/1598757" required="false">
    豆包 TTS HTTP 流式接口文档。
  </ref>
  <ref id="doubao-voice-list" url="https://www.volcengine.com/docs/6561/97465" required="false">
    豆包 TTS 1.0 音色列表。
  </ref>
  <ref id="doubao-tts-2.0-voice-list" url="https://www.volcengine.com/docs/6561/1263472" required="false">
    豆包语音合成 2.0 音色列表。
  </ref>
  <ref id="doubao-tts-2.0-api" url="https://www.volcengine.com/docs/6561/1257999" required="false">
    豆包语音合成 2.0 API 文档（含 submit/query 异步接口说明）。
  </ref>
</reference>
