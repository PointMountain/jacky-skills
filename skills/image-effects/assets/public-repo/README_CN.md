# Image Effects

为 AI 编程 Agent 提供可复用、带版本的图像效果卡，并附带一个用于浏览效果的静态 Gallery。

[English](./README.md) · [Gallery](https://wangjs-jacky.github.io/image-effects/)

## 安装

```bash
npx skills add wangjs-jacky/image-effects
```

## 使用

明确附加一张 JPEG 或 PNG 图片，然后告诉 Agent：

```text
Use $image-effects effect healing-anime-scribble-v3@1.0.0 on my uploaded image.
```

当前 MVP 只包含 1 个效果：`healing-anime-scribble-v3@1.0.0`。效果 ID 带有版本号，因此已有配方可以保持稳定，新版本也能独立演进。

## 工作方式

Skill 会解析所选效果卡、检查附件图片、把效果卡编译成图像编辑提示词，再交给宿主原生的图像生成能力。图片数据由宿主处理，本仓库不会把它上传到额外服务。Skill 无全局生成锁，因此不会把宿主中彼此无关的生成任务强制串行化。

## 贡献效果

1. 在 `references/effects/` 中新增一张带版本的效果卡，完整填写来源与许可证字段。
2. 在 `assets/previews/` 中加入一张已清除元数据的 JPEG 或 PNG 预览图。
3. 运行 Skill 包中记录的 Gallery 构建和效果验证命令。
4. 提交前检查生成的索引、Gallery 数据、预览、来源副本和第三方声明。

不要手工修改生成的 Gallery 文件或 `THIRD_PARTY_NOTICES.md`。

## 隐私与许可

只有用户明确附加的图片会交给宿主原生生成工具。处理敏感图片前，请先确认所用宿主的隐私政策。

根目录 [LICENSE](./LICENSE) 仅覆盖本仓库的原创代码与适配内容，不会重新许可第三方材料。上游署名和许可证细节见 [THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md)。
